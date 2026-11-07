"""Offline prompt contract, rendering, preservation, and rebuild regressions."""
import copy
import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import rebuild_prompts as prompts
import import_hf_readers as readers

LEGACY_FIELDS = {'id', 'name', 'source_type', 'display_type', 'prompt', 'legacy_id'}
LEGACY_DIGESTS = {'builtin-english-companion': 'fecc3ec6ef6b5c6b7a0cd0c5cf5449c756a09dfd596c77b341caf636720455a8', 'builtin-english-only': '090cd14e2441f79b632257f6df664994c508a8a9d3f995a6b8be4df9b304b0f6', 'builtin-typing-article': 'fd0865b94cc14fb29ac659174d2133f4cd4ef21c8b9eaf8a79a2c675bf48098d'}


class PromptTests(unittest.TestCase):
    def setUp(self):
        self.sources = prompts.load_prompts(ROOT)
        self.prompt = copy.deepcopy(next(p for p in self.sources if p['id'] == 'image-vocabulary-card'))

    def fixture(self, root):
        for folder in ('catalogs', 'profiles', 'prompts'):
            (root / folder).mkdir()
        p = self.prompt
        files = {
            f"prompts/{p['id']}.json": p,
            'catalogs/prompts.json': [prompts.catalog_entry(p)],
            'catalogs/summary.json': {'books': 100, 'prompts': 1},
            'profiles/default.json': {'books': ['untouched-book'], 'prompts': [p['id']],
                                     'files': ['catalogs/prompts.json', f"prompts/{p['id']}.json"],
                                     'payload_bytes': 0},
        }
        for name, value in files.items():
            (root / name).write_bytes(prompts.json_bytes(value))
        (root / 'manifest.json').write_bytes(prompts.json_bytes({
            'schema_version': 1, 'revision': 'before',
            'files': [{'path': name, 'source': {'kind': 'preserved-source'}} for name in files]}))

    def test_sources_and_counts(self):
        self.assertEqual(len(self.sources), 18)
        counts = {c: sum(p['category'] == c for p in self.sources) for c in prompts.CATEGORIES}
        self.assertEqual(counts, {'english-learning': 9, 'typing-practice': 4, 'image-generation': 5})
        for p in self.sources:
            prompts.validate_prompt(p)
            self.assertEqual(set(p['title_i18n']), {'en', 'zh-CN', 'ja'})
            self.assertEqual(p['name'], p['title_i18n']['en'])
            self.assertNotEqual(p['name'], p['title_i18n']['zh-CN'])
            self.assertNotEqual(p['name'], p['title_i18n']['ja'])

    def test_legacy_values_unchanged(self):
        for p in self.sources:
            if p['id'] in LEGACY_DIGESTS:
                original = {key: p[key] for key in LEGACY_FIELDS}
                digest = hashlib.sha256(json.dumps(original, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                self.assertEqual(digest, LEGACY_DIGESTS[p['id']])
        self.assertEqual(len(LEGACY_DIGESTS), 3)

    def test_new_ids_do_not_invent_legacy_ids(self):
        self.assertEqual({p['id'] for p in self.sources if 'legacy_id' in p}, set(LEGACY_DIGESTS))

    def test_defaults_render_every_prompt(self):
        for p in self.sources:
            body = prompts.render_prompt(p)
            self.assertTrue(body.strip())
            self.assertNotIn('{{', body)
            self.assertNotIn('}}', body)
            if not p['variables']:
                self.assertEqual(body, p['prompt'])

    def test_literal_override_does_not_evaluate_code_or_backslashes(self):
        value = 'pear $HOME \\1 "quoted"'
        result = prompts.render_prompt(self.prompt, {'word': value})
        self.assertIn(value, result)
        self.assertNotIn('{{word}}', result)
        self.assertIn('simple flat illustration', result)

    def test_unknown_empty_nonstring_nested_overrides_rejected(self):
        for value in ({'unknown': 'a'}, {'word': ''}, {'word': None}, {'word': '{{style}}'}, [], 4):
            with self.subTest(value=value), self.assertRaises(ValueError):
                prompts.render_prompt(self.prompt, value)

    def test_missing_extra_or_malformed_placeholders_rejected(self):
        for suffix in (' {{missing}}', ' {{ word }}', ' {{word', ' word}}'):
            bad = copy.deepcopy(self.prompt)
            bad['prompt'] += suffix
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                prompts.validate_prompt(bad)
        self.prompt['variables'].append({'name': 'unused', 'default': 'x', 'description': 'Unused.'})
        with self.assertRaisesRegex(ValueError, 'Placeholder/variable mismatch'):
            prompts.validate_prompt(self.prompt)

    def test_duplicate_variable_rejected(self):
        self.prompt['variables'].append(copy.deepcopy(self.prompt['variables'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate variable'):
            prompts.validate_prompt(self.prompt)

    def test_variable_metadata_rejected(self):
        for patch in ({'name': 'Bad name'}, {'default': '{{word}}'}, {'default': ' padded '}, {'extra': 'field'}):
            bad = copy.deepcopy(self.prompt)
            bad['variables'][0].update(patch)
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                prompts.validate_prompt(bad)

    def test_invalid_translations_rejected(self):
        for value in ({'en': self.prompt['name']}, [], {'en': self.prompt['name'], 'zh': '卡片', 'ja': 'カード'}):
            bad = copy.deepcopy(self.prompt)
            bad['title_i18n'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                prompts.validate_prompt(bad)
        for value in ('', ' padded ', 'bad\nline', 'bad\u202etext', None, 5):
            bad = copy.deepcopy(self.prompt)
            bad['title_i18n']['zh-CN'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                prompts.validate_prompt(bad)

    def test_english_fallback_equality_required(self):
        self.prompt['title_i18n']['en'] = 'A different title'
        with self.assertRaisesRegex(ValueError, 'English title differs'):
            prompts.validate_prompt(self.prompt)

    def test_invalid_types_and_enums_rejected(self):
        for key, value in [('id', '../escape'), ('source_type', 'private'), ('display_type', 'image'),
                           ('output_type', 'audio'), ('prompt_role', 'admin'), ('category', 'unknown'),
                           ('cefr_levels', ['A3']), ('tags', ['card', 'card']), ('legacy_id', True),
                           ('prompt', ''), ('variables', None)]:
            bad = copy.deepcopy(self.prompt)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                prompts.validate_prompt(bad)

    def test_image_routing_consistency_required(self):
        for key, value in [('output_type', 'text'), ('display_type', 'reading')]:
            bad = copy.deepcopy(self.prompt)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                prompts.validate_prompt(bad)

    def test_catalog_metadata_matches_sources(self):
        catalog = json.loads((ROOT / 'catalogs/prompts.json').read_text())
        by_id = {p['id']: p for p in self.sources}
        self.assertEqual(set(by_id), {p['id'] for p in catalog})
        for item in catalog:
            self.assertEqual(item, prompts.catalog_entry(by_id[item['id']]))
            self.assertNotIn('prompt', item)

    def test_no_duplicate_bodies(self):
        self.assertEqual(len({p['prompt'] for p in self.sources}), len(self.sources))

    def test_filename_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.fixture(root)
            source = root / f"prompts/{self.prompt['id']}.json"
            renamed = source.with_name('wrong-id.json')
            source.rename(renamed)
            with self.assertRaisesRegex(ValueError, 'filename/ID mismatch'):
                prompts.load_prompts(root)
            renamed.rename(source)
            alias = source.with_name('alias.json')
            alias.symlink_to(source)
            with self.assertRaisesRegex(ValueError, 'Symlinked prompt'):
                prompts.load_prompts(root)

    def test_plan_is_idempotent_and_preserves_other_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.fixture(root)
            first = prompts.make_plan(root)
            self.assertEqual(json.loads(first['catalogs/summary.json'])['books'], 100)
            self.assertEqual(json.loads(first['profiles/default.json'])['books'], ['untouched-book'])
            for name, data in first.items():
                (root / name).write_bytes(data)
            second = prompts.make_plan(root)
            self.assertEqual(first, second)
            self.assertEqual(json.loads(first['manifest.json'])['revision'], 'before')
            for item in json.loads(first['manifest.json'])['files']:
                self.assertEqual(item['source'], {'kind': 'preserved-source'})

    def test_append_new_prompt_preserves_order_and_includes_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.fixture(root)
            added = copy.deepcopy(self.prompt)
            added['id'] = 'another-card'
            (root / 'prompts/another-card.json').write_bytes(prompts.json_bytes(added))
            plan = prompts.make_plan(root)
            self.assertEqual([p['id'] for p in json.loads(plan['catalogs/prompts.json'])], [self.prompt['id'], 'another-card'])
            profile = json.loads(plan['profiles/default.json'])
            self.assertIn('another-card', profile['prompts'])
            self.assertIn('prompts/another-card.json', profile['files'])
            self.assertEqual(json.loads(plan['catalogs/summary.json'])['prompts'], 2)
            for name, data in plan.items():
                (root / name).write_bytes(data)
            self.assertEqual(prompts.make_plan(root), plan)

    def test_removing_existing_prompt_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.fixture(root)
            catalog = [prompts.catalog_entry(self.prompt), {'id': 'missing-original'}]
            (root / 'catalogs/prompts.json').write_bytes(prompts.json_bytes(catalog))
            with self.assertRaisesRegex(ValueError, 'Removing existing prompts'):
                prompts.make_plan(root)

    def test_untracked_private_file_and_missing_recorded_file_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.fixture(root)
            private = root / 'private.txt'
            private.write_text('Not a resource')
            with self.assertRaisesRegex(ValueError, 'Unexpected local files'):
                prompts.make_plan(root)
            private.unlink()
            manifest = json.loads((root / 'manifest.json').read_text())
            manifest['files'].append({'path': 'missing-original.txt'})
            (root / 'manifest.json').write_bytes(prompts.json_bytes(manifest))
            with self.assertRaisesRegex(ValueError, 'Removing recorded files'):
                prompts.make_plan(root)

    def test_repository_plan_has_no_changes(self):
        for name, data in prompts.make_plan(ROOT).items():
            self.assertEqual((ROOT / name).read_bytes(), data, name)

    def test_noop_book_import_preserves_prompt_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            for folder in ('catalogs', 'profiles'):
                (root / folder).mkdir()
            files = {'catalogs/books.json': [], 'catalogs/summary.json': {'books': 0, 'chapters': 0, 'prompts': 18},
                     'profiles/default.json': {'books': [], 'files': [], 'payload_bytes': 0}}
            for name, value in files.items():
                (root / name).write_bytes(prompts.json_bytes(value))
            (root / 'manifest.json').write_bytes(prompts.json_bytes({'schema_version': 1, 'revision': 'newer-prompt-catalog',
                                                                    'files': [{'path': p} for p in files]}))
            plan = readers.make_plan(root, {'import_id': 'test', 'revision': 'older-book-import'}, [], {})
            self.assertEqual(json.loads(plan['manifest.json'])['revision'], 'newer-prompt-catalog')
            self.assertEqual(json.loads(plan['catalogs/summary.json'])['prompts'], 18)


if __name__ == '__main__':
    unittest.main()
