#!/usr/bin/env python3
"""Rebuild localized dictionary titles and compact manifest offline.

Only known supporting files may be newly inventoried. Resource contents and
legacy names are preserved. --check verifies deterministic output.
"""
import argparse
import copy
import json
from import_hf_readers import ROOT, apply_plan, json_bytes, require, resource_files, safe_path, sha256, recover_transaction, transaction_directory
from manifest_io import load_manifest, finish_manifest

SUPPORT = {'tools/manifest_io.py', 'tools/rebuild_metadata.py', 'tools/dictionary_titles.json',
           'tests/test_manifest_io.py', 'tests/test_dictionary_titles.py', 'docs/compact-manifest.md'}
LOCALES = {'en', 'zh-CN', 'ja'}


def localized_dictionaries(rows, titles):
    require(titles.get('schema_version') == 1, 'Unsupported dictionary title version')
    translations = titles.get('dictionaries', {})
    require(set(translations) == {r['id'] for r in rows}, 'Dictionary title coverage differs')
    result = copy.deepcopy(rows)
    for row in result:
        value = translations[row['id']]
        require(isinstance(value, dict) and set(value) == LOCALES, 'Missing title locales: ' + row['id'])
        require(all(isinstance(s, str) and s.strip() == s and s and not any(ord(c) < 32 for c in s)
                    for s in value.values()), 'Invalid dictionary title: ' + row['id'])
        if row.get('title_i18n') != value:
            row['title_i18n'] = copy.deepcopy(value)
            row['revision'] += 1
    return result


def make_plan(root):
    manifest = load_manifest(root)
    recorded = {r['path']: r for r in manifest['files']}
    rows = json.loads((root / 'catalogs/dictionaries.json').read_text())
    titles = json.loads((root / 'tools/dictionary_titles.json').read_text())
    outputs = {'catalogs/dictionaries.json': json_bytes(localized_dictionaries(rows, titles))}
    profile = json.loads((root / 'profiles/default.json').read_text())
    profile['payload_bytes'] = sum(len(outputs[p]) if p in outputs else safe_path(root, p).stat().st_size for p in profile['files'])
    outputs['profiles/default.json'] = json_bytes(profile)
    actual = {p.relative_to(root).as_posix() for p in resource_files(root)}
    require(not set(recorded) - actual, 'Missing recorded files')
    require(not actual - set(recorded) - SUPPORT, 'Unexpected local files: ' + str(actual - set(recorded) - SUPPORT))
    files = []
    for name in sorted(actual | set(outputs)):
        path = safe_path(root, name)
        require(not path.is_symlink(), 'Symlinked resource: ' + name)
        data = outputs[name] if name in outputs else path.read_bytes()
        record = dict(recorded.get(name, {}))
        record.update(path=name, bytes=len(data), sha256=sha256(data))
        record.setdefault('content_type', {'.py':'text/x-python','.json':'application/json','.md':'text/markdown'}.get(path.suffix,'application/octet-stream'))
        record.setdefault('category', 'documentation' if name.startswith('docs/') else 'tooling')
        files.append(record)
    manifest['files'] = files
    if manifest.get('schema_version') != 2 or outputs['catalogs/dictionaries.json'] != (root/'catalogs/dictionaries.json').read_bytes():
        manifest['revision'] = '2026-11-07-lightweight-manifest-v2'
    finish_manifest(manifest, outputs)
    return outputs


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--write', action='store_true'); mode.add_argument('--check', action='store_true')
    mode.add_argument('--recover', action='store_true', help='Recover an interrupted atomic write')
    args = p.parse_args()
    if args.recover:
        recover_transaction(ROOT)
        print('Recovered interrupted metadata update')
        return
    require(not transaction_directory(ROOT).exists(), 'Interrupted import exists; run --recover first')
    plan = make_plan(ROOT)
    changed = [f for f, data in plan.items() if not (ROOT/f).is_file() or (ROOT/f).read_bytes() != data]
    if args.check: require(not changed, 'Rebuild differs: ' + str(changed))
    if args.write: apply_plan(ROOT, plan, changed)
    print(json.dumps({'status':'ok','changed_files':changed,'manifest_bytes':len(plan['manifest.json'])}))

if __name__ == '__main__': main()
