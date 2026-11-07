"""Lightweight v2 discovery manifest, lazy integrity inventory and audit index.

All payload paths and hashes are preserved in the separately fetched inventory.
Catalog/profile references are directly verifiable without loading that inventory.
"""
import copy
import hashlib
import json
import pathlib

SOURCE_PATH = 'catalogs/file-sources.json'
INVENTORY_PATH = 'catalogs/files.json'


def compact_bytes(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')


def manifest_bytes(value):
    # One file per line: compact on the wire, useful line-based diffs in Git.
    fields = []
    for key, item in value.items():
        if key == 'files':
            rendered = '[\n' + ',\n'.join('    ' + compact_bytes(v).decode().strip() for v in item) + '\n  ]'
        else:
            rendered = compact_bytes(item).decode().strip()
        fields.append('  ' + json.dumps(key) + ': ' + rendered)
    return ('{\n' + ',\n'.join(fields) + '\n}\n').encode('utf-8')


def load_manifest(root):
    manifest = json.loads((root / 'manifest.json').read_text())
    version = manifest.get('schema_version')
    if version == 2:
        if 'files' in manifest:
            raise ValueError('V2 manifest must not contain inline files')
        ref = manifest.get('file_inventory', {})
        if ref.get('path') != INVENTORY_PATH:
            raise ValueError('Unsupported file inventory path')
        path = root / INVENTORY_PATH
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Unsafe file inventory path')
        data = path.read_bytes()
        if len(data) != ref.get('bytes') or hashlib.sha256(data).hexdigest() != ref.get('sha256'):
            raise ValueError('File inventory integrity mismatch')
        inventory = json.loads(data)
        if inventory.get('schema_version') != 1 or not isinstance(inventory.get('files'), list):
            raise ValueError('Unsupported file inventory schema')
        records = inventory['files']
        if any(v.get('path') in ('manifest.json', INVENTORY_PATH) for v in records):
            raise ValueError('Circular file inventory entry')
        if len({v['path'] for v in records}) != len(records):
            raise ValueError('Duplicate file inventory entry')
        lookup = {v['path']: v for v in records}
        references = [item for section in ('catalogs', 'profiles', 'compatibility')
                      for item in manifest.get(section, {}).values()]
        if manifest.get('file_sources'):
            references.append(manifest['file_sources'])
        for item in references:
            record = lookup.get(item.get('path'))
            if record is None or any(item.get(k) != record.get(k) for k in ('bytes', 'sha256')):
                raise ValueError('Discovery reference differs from inventory: ' + str(item.get('path')))
        manifest['files'] = records + [{**ref, 'content_type':'application/json', 'category':'catalog'}]
    elif version != 1:
        raise ValueError('Unsupported manifest version')
    reference = manifest.get('file_sources')
    if reference is None:
        return manifest
    if reference.get('path') != SOURCE_PATH:
        raise ValueError('Unsupported file source index path')
    path = root / SOURCE_PATH
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Unsafe file source index')
    data = path.read_bytes()
    records = {v['path']: v for v in manifest['files']}
    record = records.get(SOURCE_PATH, {})
    if len(data) != record.get('bytes') or hashlib.sha256(data).hexdigest() != record.get('sha256'):
        raise ValueError('File source index integrity mismatch')
    index = json.loads(data)
    if index.get('schema_version') != 1 or not isinstance(index.get('sources'), list) or not isinstance(index.get('files'), dict):
        raise ValueError('Unsupported file source index')
    for name, source_id in index['files'].items():
        if name not in records or type(source_id) is not int or not 0 <= source_id < len(index['sources']):
            raise ValueError('Invalid file source reference: ' + name)
        source = index['sources'][source_id]
        if not isinstance(source, dict) or 'source' in records[name]:
            raise ValueError('Invalid or duplicate file source: ' + name)
        records[name]['source'] = copy.deepcopy(source)
    return manifest


def finish_manifest(manifest, outputs):
    """Serialize full records to compact manifest + sidecar, without data loss."""
    result = copy.deepcopy(manifest)
    sources, ids, files = [], {}, {}
    records = [v for v in result['files'] if v['path'] not in (SOURCE_PATH, INVENTORY_PATH)]
    # Stable source IDs depend only on sorted file paths, not caller order.
    for record in sorted(records, key=lambda v: v['path']):
        if 'source' not in record:
            continue
        source = record.pop('source')
        key = json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        if key not in ids:
            ids[key] = len(sources)
            sources.append(source)
        files[record['path']] = ids[key]
    index = compact_bytes({'schema_version': 1, 'sources': sources, 'files': files})
    outputs[SOURCE_PATH] = index
    records.append({'path': SOURCE_PATH, 'bytes': len(index), 'sha256': hashlib.sha256(index).hexdigest(),
                    'content_type': 'application/json', 'category': 'catalog'})
    records = sorted(records, key=lambda v: v['path'])
    inventory = manifest_bytes({'schema_version': 1, 'files': records})
    outputs[INVENTORY_PATH] = inventory
    result.pop('files', None)
    result['schema_version'] = 2
    result['file_sources'] = {'path': SOURCE_PATH}
    lookup = {v['path']: v for v in records}
    # Catalog discovery stays small and is verifiable without the full inventory.
    for section in ('catalogs', 'profiles', 'compatibility'):
        for name, ref in result.get(section, {}).items():
            record = lookup[ref['path']]
            result[section][name] = {k: record[k] for k in ('path','bytes','sha256')}
    result['file_sources'] = {k: lookup[SOURCE_PATH][k] for k in ('path','bytes','sha256')}
    result['file_inventory'] = {'path': INVENTORY_PATH, 'bytes': len(inventory),
                                'sha256': hashlib.sha256(inventory).hexdigest()}
    result['total_bytes'] = sum(v['bytes'] for v in records) + len(inventory)
    outputs['manifest.json'] = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
