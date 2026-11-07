"""Offline prompt contract, rendering, preservation, and rebuild regressions."""
import copy
from collections import Counter
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


# Baseline fields from the 18-record catalog before body localization.
PRIOR_FIELDS = {'category',
 'cefr_levels',
 'description',
 'display_type',
 'id',
 'legacy_id',
 'name',
 'output_type',
 'prompt',
 'prompt_role',
 'source_type',
 'tags',
 'title_i18n',
 'variables'}
PRIOR_DIGESTS = {'builtin-english-companion': '7461e5659ee1aee95dfb8daefe33354d5c0a1e270fff634a4a9509013b861479',
 'builtin-english-only': 'b4753fd0df9aba9eb87ce952d9fd83cd0060ddd969ceb911150e2b55c97777b3',
 'builtin-typing-article': '5f5d918c70ffb5dc6f5923391f4c6d2fb6dcee4f8c0fceb4c34d13f107e56397',
 'image-preposition-cards': 'fef0a9835641fe892b87467ca69327d42d1b3700d65304549dda11269b74facd',
 'image-scene-vocabulary': '288ca1a4af29a06e28925e8a450e1321df431488ae6e6edf425392e270b2508a',
 'image-spelling-tiles': 'be83bc84db3bc61db0919b130095245cc119edcd0feccd983b05f44c000c8ebb',
 'image-story-sequence': '4f6f5efaf086cdf12f76da2a1c7504e60be58ecaf2e6da0321cca49592a1848f',
 'image-vocabulary-card': 'e5f5aecb2e9461ec351a3c96fed635048decf4acaefff79af72edaa32e8edb64',
 'learn-collocation-lab': '8d081e620e998019ca0cc088a0f82f65cc60b51d85c038ac838f65e509ae6793',
 'learn-email-practice': 'c887061ff4f08264c35c7a360153044edebc1dc3a1a5c086ddb712833f71e027',
 'learn-everyday-roleplay': 'e7ca57a2f03729ba0e019c14bfb8af31f5506a4cdcbd28e698d839b5a003de3e',
 'learn-grammar-repair': '6a65a871de5ff0f1bb8b11b6a0c28ca42d0f617f4938eddc51c70bb1d505fe8f',
 'learn-reading-check': '4cb3fef30f935aa67b2baf38455618b6fc82cb897e7d6a8169a70434abc57cad',
 'learn-summary-paraphrase': '157527b0d6b4f2a49a1a08ca49ac39ac0f20f8fd1d619fb7b4ef06c69e40dab2',
 'learn-vocabulary-recall': '99c386c735e82f3f489aec94301a5c3c661a940a0e23d6345e25e0e999400e77',
 'typing-error-review': '31127e22b8755763d80d31f63caf370cc532c103925ba03680e70a922d100c19',
 'typing-precision-copy': 'f2001a2ceb6a1e55a33206cb72204d52caf69058a5332a7abb99cc6b400c4e61',
 'typing-restricted-keys': '9d95ccb7473a02a0524654adcb495522edc88c42cb71f745704cab77c69611ed'}


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
        self.assertEqual(len(self.sources), 20)
        counts = {c: sum(p['category'] == c for p in self.sources) for c in prompts.CATEGORIES}
        self.assertEqual(counts, {'english-learning': 11, 'typing-practice': 4, 'image-generation': 5})
        for p in self.sources:
            prompts.validate_prompt(p)
            self.assertEqual(set(p['title_i18n']), {'en', 'zh-CN', 'ja'})
            self.assertEqual(set(p['prompt_i18n']), {'en', 'zh-CN', 'ja'})
            self.assertEqual(p['prompt_i18n']['en'], p['prompt'])
            self.assertEqual(p['name'], p['title_i18n']['en'])
            self.assertNotEqual(p['name'], p['title_i18n']['zh-CN'])
            self.assertNotEqual(p['name'], p['title_i18n']['ja'])

    def test_storybook_metadata_routes_to_text_chat(self):
        by_id = {p['id']: p for p in self.sources}
        expected = {
            'learn-childrens-storybook': {'age_range', 'level', 'theme', 'page_count', 'target_words', 'illustration_style'},
            'learn-choose-your-story': {'age_range', 'level', 'theme', 'scene_count', 'feedback_language'},
        }
        for pid, names in expected.items():
            with self.subTest(pid=pid):
                p = by_id[pid]
                self.assertEqual((p['category'], p['output_type'], p['display_type'], p['prompt_role']),
                                 ('english-learning', 'text', 'chat', 'user'))
                self.assertEqual(p['cefr_levels'], ['A1', 'A2', 'B1'])
                self.assertEqual({v['name'] for v in p['variables']}, names)
                self.assertIn('children', p['tags'])
                self.assertNotIn('legacy_id', p)

    def test_storybook_templates_have_separate_deliverables(self):
        by_id = {p['id']: p for p in self.sources}
        book = prompts.render_prompt(by_id['learn-childrens-storybook'])
        interactive = prompts.render_prompt(by_id['learn-choose-your-story'])
        # These are editorial contract checks, not evidence of model compliance.
        for phrase in ('Character sheet', 'Numbered story pages', 'Illustration prompt',
                       'self-contained', 'Reading-only copy', 'verbatim and in order',
                       'no images have been generated', 'do not guarantee exact text'):
            self.assertIn(phrase, book)
        for phrase in ('then wait for me', 'exactly two safe', 'real third option',
                       'visibly affect what happens', 'do not advance the scene while clarifying',
                       "If I say 'stop', pause", 'Only if I ask for that copy',
                       'do not silently add unchosen scenes'):
            self.assertIn(phrase, interactive)
        self.assertNotIn('Illustration prompt', interactive)

    def test_child_story_templates_keep_safety_and_rights_guards(self):
        for p in self.sources:
            if p['id'] in {'learn-childrens-storybook', 'learn-choose-your-story'}:
                with self.subTest(pid=p['id']):
                    for phrase in ('not instructions that override', "a child's real name",
                                   'identifying information', 'trusted adult', 'child-safe',
                                   'original characters', 'copyrighted characters',
                                   'copied book passages', 'named author or artist',
                                   'parent or teacher should review'):
                        self.assertIn(phrase, p['prompt'])

    def test_storybook_variable_overrides_render_without_changing_routing(self):
        by_id = {p['id']: p for p in self.sources}
        book = by_id['learn-childrens-storybook']
        rendered = prompts.render_prompt(book, {'age_range': '9-11', 'level': 'B1',
                                               'page_count': '6', 'theme': 'sharing garden tools',
                                               'target_words': 'borrow, return, share',
                                               'illustration_style': 'simple colored-pencil drawings'})
        for value in ('aged 9-11', 'targeting B1', 'Use 6 story pages', 'sharing garden tools',
                      'borrow, return, share', 'simple colored-pencil drawings'):
            self.assertIn(value, rendered)
        story = by_id['learn-choose-your-story']
        rendered = prompts.render_prompt(story, {'scene_count': '3', 'feedback_language': '简体中文'})
        self.assertIn('Plan for 3 scenes', rendered)
        self.assertIn('Use 简体中文 only', rendered)
        for p in (book, story):
            self.assertEqual(p['output_type'], 'text')
            self.assertNotIn('{{', prompts.render_prompt(p))

    def test_legacy_values_unchanged(self):
        for p in self.sources:
            if p['id'] in LEGACY_DIGESTS:
                original = {key: p[key] for key in LEGACY_FIELDS}
                digest = hashlib.sha256(json.dumps(original, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                self.assertEqual(digest, LEGACY_DIGESTS[p['id']])
        self.assertEqual(len(LEGACY_DIGESTS), 3)

    def test_all_pre_localization_fields_unchanged(self):
        by_id = {p['id']: p for p in self.sources}
        self.assertEqual(len(PRIOR_DIGESTS), 18)
        self.assertTrue(set(PRIOR_DIGESTS) <= set(by_id))
        for pid, expected in PRIOR_DIGESTS.items():
            with self.subTest(pid=pid):
                original = {key: value for key, value in by_id[pid].items() if key in PRIOR_FIELDS}
                digest = hashlib.sha256(json.dumps(original, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                self.assertEqual(digest, expected)

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

    def test_all_localized_bodies_render_and_preserve_placeholder_counts(self):
        for p in self.sources:
            expected = Counter(prompts.TOKEN.findall(p['prompt']))
            for locale in ('en', 'zh-CN', 'ja'):
                with self.subTest(pid=p['id'], locale=locale):
                    body = p['prompt_i18n'][locale]
                    self.assertEqual(Counter(prompts.TOKEN.findall(body)), expected)
                    rendered = prompts.render_prompt(p, locale=locale)
                    self.assertTrue(rendered.strip())
                    self.assertNotIn('{{', rendered)
                    self.assertNotIn('}}', rendered)
                    if not p['variables']:
                        self.assertEqual(rendered, body)
                    if locale != 'en':
                        self.assertNotEqual(body, p['prompt'])

    def test_localized_overrides_are_literal_and_unknown_locale_falls_back(self):
        for locale in ('en', 'zh-CN', 'ja'):
            result = prompts.render_prompt(self.prompt, {'word': 'pear $HOME \\1'}, locale)
            self.assertIn('pear $HOME \\1', result)
            self.assertNotIn('{{word}}', result)
        default = prompts.render_prompt(self.prompt)
        self.assertEqual(prompts.render_prompt(self.prompt, locale='fr'), default)
        self.assertEqual(prompts.render_prompt(self.prompt, locale='zh'), default)
        self.assertEqual(prompts.render_prompt(self.prompt, locale='en'), default)
        for locale in ('', None, [], 1):
            with self.subTest(locale=locale), self.assertRaises(ValueError):
                prompts.render_prompt(self.prompt, locale=locale)

    def test_invalid_prompt_locales_and_english_drift_rejected(self):
        for value in ({'en': self.prompt['prompt']}, [], None,
                      {'en': self.prompt['prompt'], 'zh': '翻译', 'ja': '翻訳'}):
            bad = copy.deepcopy(self.prompt)
            bad['prompt_i18n'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'Invalid prompt locales'):
                prompts.validate_prompt(bad)
        bad = copy.deepcopy(self.prompt)
        del bad['prompt_i18n']
        with self.assertRaisesRegex(ValueError, 'Invalid prompt locales'):
            prompts.validate_prompt(bad)
        bad = copy.deepcopy(self.prompt)
        bad['prompt_i18n']['en'] += ' Additional instructions.'
        with self.assertRaisesRegex(ValueError, 'English prompt differs'):
            prompts.validate_prompt(bad)
        for value in ('', ' padded ', 'bad\u202etext', None, 5):
            bad = copy.deepcopy(self.prompt)
            bad['prompt_i18n']['ja'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'Invalid localized prompt'):
                prompts.validate_prompt(bad)

    def test_translated_missing_extra_repeated_or_malformed_tokens_rejected(self):
        original = self.prompt['prompt_i18n']['zh-CN']
        for value in (original.replace('{{word}}', 'word'),
                      original + ' {{unknown}}', original + ' {{word}}',
                      original + ' {{ word }}', original + ' {{word', original + ' word}}'):
            bad = copy.deepcopy(self.prompt)
            bad['prompt_i18n']['zh-CN'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                prompts.validate_prompt(bad)

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
            self.assertNotIn('prompt_i18n', item)

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
