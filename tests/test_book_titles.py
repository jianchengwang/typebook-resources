"""Offline coverage and backwards-compatibility checks for display titles."""
import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('reader_titles', ROOT / 'tools/import_hf_readers.py')
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


class BookTitleTests(unittest.TestCase):
    def setUp(self):
        self.books = [{'id': 'book:1', 'title': 'A Christmas Carol', 'revision': 2,
                       'author': 'Charles Dickens', 'license_status': 'not-recorded-in-source',
                       'chapters': [{'id': 'chapter:1', 'title': 'Chapter 1', 'body': {'path': 'unchanged.txt', 'sha256': 'original'}}]}]
        self.titles = {'schema_version': 1, 'books': {'book:1': {
            'en': 'A Christmas Carol', 'zh-CN': '圣诞颂歌', 'ja': 'クリスマス・キャロル'}}}

    def apply(self):
        return reader.apply_title_translations(self.books, self.titles, self.books)

    def test_only_title_metadata_and_revision_change(self):
        before = copy.deepcopy(self.books)
        localized = self.apply()[0]
        self.assertEqual(localized.pop('title_i18n'), self.titles['books']['book:1'])
        self.assertEqual(localized.pop('revision'), 3)
        original = copy.deepcopy(before[0])
        original.pop('revision')
        self.assertEqual(localized, original)
        self.assertEqual(self.books, before)

    def test_idempotent_revision(self):
        first = self.apply()
        self.assertEqual(reader.apply_title_translations(self.books, self.titles, first), first)
        self.assertEqual(reader.apply_title_translations(first, self.titles, first), first)

    def test_later_translation_edit_bumps_revision_once(self):
        first = self.apply()
        self.titles['books']['book:1']['zh-CN'] = '圣诞赞歌'
        second = reader.apply_title_translations(self.books, self.titles, first)
        self.assertEqual(second[0]['revision'], 4)
        self.assertEqual(reader.apply_title_translations(self.books, self.titles, second), second)

    def test_new_book_keeps_initial_revision(self):
        result = reader.apply_title_translations(self.books, self.titles, [])
        self.assertEqual(result[0]['revision'], 2)

    def test_english_title_cannot_be_rewritten(self):
        self.titles['books']['book:1']['en'] = 'Rewritten title'
        with self.assertRaisesRegex(ValueError, 'English title differs'): self.apply()

    def test_missing_book_rejected(self):
        self.titles['books'].clear()
        with self.assertRaisesRegex(ValueError, 'book IDs differ'): self.apply()

    def test_unknown_book_rejected(self):
        self.titles['books']['book:404'] = self.titles['books']['book:1']
        with self.assertRaisesRegex(ValueError, 'book IDs differ'): self.apply()

    def test_missing_or_unknown_locale_rejected(self):
        for locales in ({'en': 'A Christmas Carol'}, {'en': 'A Christmas Carol', 'zh': '圣诞颂歌', 'ja': 'クリスマス・キャロル'}, []):
            with self.subTest(locales=locales):
                self.titles['books']['book:1'] = locales
                with self.assertRaisesRegex(ValueError, 'title locale'): self.apply()

    def test_empty_padded_and_control_characters_rejected(self):
        for value in ('', ' ', ' 圣诞颂歌', '圣诞颂歌\n', '圣诞\x00颂歌', '圣诞\u202e颂歌', None, 1):
            with self.subTest(value=value):
                self.titles['books']['book:1']['zh-CN'] = value
                with self.assertRaisesRegex(ValueError, 'Invalid localized title'): self.apply()

    def test_schema_rejected(self):
        self.titles['schema_version'] = 99
        with self.assertRaisesRegex(ValueError, 'translation schema'): self.apply()

    def test_generated_plan_uses_configured_titles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            for folder in ('catalogs', 'profiles', 'tools'): (root / folder).mkdir()
            book = {**self.books[0], 'chapter_count': 1}
            data = {'catalogs/books.json': [book], 'catalogs/summary.json': {'books': 1, 'chapters': 1},
                    'profiles/default.json': {'books': ['book:1'], 'files': ['catalogs/books.json'], 'payload_bytes': 0},
                    'tools/book_titles.json': self.titles}
            for name, value in data.items(): (root / name).write_bytes(reader.json_bytes(value))
            manifest = {'schema_version': 1, 'files': [{'path': name} for name in data]}
            (root / 'manifest.json').write_bytes(reader.json_bytes(manifest))
            config = {'import_id': 'test', 'revision': 'localized', 'title_translations_path': 'tools/book_titles.json'}
            plan = reader.make_plan(root, config, [], {})
            self.assertEqual(json.loads(plan['catalogs/books.json'])[0]['title_i18n'], self.titles['books']['book:1'])
            for name, value in plan.items(): (root / name).write_bytes(value)
            self.assertEqual(reader.make_plan(root, config, [], {}), plan)

    def test_full_catalog_has_exact_translation_coverage(self):
        books = json.loads((ROOT / 'catalogs/books.json').read_text())
        books += json.loads((ROOT / 'catalogs/standalone-readers.json').read_text())
        titles = json.loads((ROOT / 'tools/book_titles.json').read_text())
        localized = reader.apply_title_translations(books, titles, books)
        self.assertEqual(len(books), 104)
        self.assertEqual(localized, books)
        for book in books:
            self.assertEqual(book['title'], book['title_i18n']['en'])
            self.assertNotEqual(book['title_i18n']['zh-CN'], book['title'])
            self.assertNotEqual(book['title_i18n']['ja'], book['title'])


if __name__ == '__main__':
    unittest.main()
