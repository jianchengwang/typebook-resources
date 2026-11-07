"""Compact v1 manifests with optional, deduplicated source-audit metadata.

Runtime file records retain every path, byte length, SHA-256, MIME type and
category. Only the optional `source` field moves to an integrity-checked sidecar.
"""
import copy
import hashlib
import json
import pathlib

SOURCE_PATH = 'catalogs/file-sources.json'


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
    reference = manifest.get('file_sources')
    if reference is None:
        return manifest
    if reference != {'path': SOURCE_PATH}:
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
    records = [v for v in result['files'] if v['path'] != SOURCE_PATH]
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
    result['files'] = sorted(records, key=lambda v: v['path'])
    result['file_sources'] = {'path': SOURCE_PATH}
    result['total_bytes'] = sum(v['bytes'] for v in result['files'])
    outputs['manifest.json'] = manifest_bytes(result)
