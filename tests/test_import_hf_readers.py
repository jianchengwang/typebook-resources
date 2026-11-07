"""Offline regression tests for the curated reader importer."""
import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

MODULE = pathlib.Path(__file__).resolve().parents[1] / "tools/import_hf_readers.py"
spec = importlib.util.spec_from_file_location("import_hf_readers", MODULE)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "schema_version": 1, "import_id": "test-readers", "revision": "test-1",
            "dataset": {"repository": "cis-lmu/GlotStoryBook", "revision": "a" * 40, "filename": "GlotStoryBook.csv", "sha256": "a" * 64, "bytes": 1},
            "upstream": {"repository": "global-asp/asp-source", "revision": "b" * 40, "index_path": "en/README.md", "index_sha256": "b" * 64},
            "books": [{"slug": "asp-test-reader", "legacy_id": 800001, "chapter_legacy_id": 800001, "parallel_id": "asp_0001", "filename": "0001_test-reader.md", "title": "Test reader", "author": "Example Writer", "license_id": "CC-BY-3.0", "license_url": "https://creativecommons.org/licenses/by/3.0/", "original_url": "https://example.org/story", "source_sha256": "c" * 64, "paragraph_count": 2, "word_count": 6, "practice_band": "starter", "practice_note": "Simple test sentences."}],
        }
        self.csv = ('Text,Text Number,License,Text By,Translation By,Language,File Name,Source,ISO639-3,Script,Parallel ID,Story Category\n'
                    'I can read.,0,CC-BY,Example Writer,,en,0001_test-reader.md,global-asp/asp-source,eng,Latn,asp_0001,asp\n'
                    'We read together.,1,CC-BY,Example Writer,,en,0001_test-reader.md,global-asp/asp-source,eng,Latn,asp_0001,asp\n').encode()
        self.index = b'0001 | [Test reader](https://example.org/story) | [CC-BY](https://creativecommons.org/licenses/by/3.0/)\n'
        self.originals = {"0001_test-reader.md": b'# Test reader\n\n##\nI can read.\n\n##\nWe read together.\n\n##\n* License: [CC-BY]\n* Text: Example Writer\n* Language: en\n'}

    def build(self):
        return reader.build_books(self.config, self.csv, self.index, self.originals)

    def test_valid_story_preserves_paragraphs(self):
        books, files = self.build()
        self.assertEqual(files['books/asp-test-reader/chapters/001.txt'], b'I can read.\n\nWe read together.\n')
        self.assertEqual(books[0]['word_count'], 6)
        self.assertEqual(books[0]['chapter_count'], 1)
        self.assertIn(b'CC-BY-3.0', files['books/asp-test-reader/LICENSE.md'])

    def test_typographic_normalization(self):
        self.assertEqual(reader.normalize('  “I’m here”\n  now—yes. '), '"I\'m here" now-yes.')

    def test_dataset_nc_rejected(self):
        self.csv = self.csv.replace(b',CC-BY,', b',CC-BY-NC,')
        with self.assertRaisesRegex(ValueError, 'metadata disagreement'): self.build()

    def test_original_nc_rejected(self):
        self.originals = {key: value.replace(b'[CC-BY]', b'[CC-BY-NC]') for key, value in self.originals.items()}
        with self.assertRaisesRegex(ValueError, 'not CC BY'): self.build()

    def test_index_nc_rejected(self):
        self.index = self.index.replace(b'licenses/by/', b'licenses/by-nc/')
        with self.assertRaisesRegex(ValueError, 'license disagreement'): self.build()

    def test_missing_license_rejected(self):
        self.config['books'][0]['license_id'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'Unapproved license'): self.build()

    def test_language_rejected(self):
        self.csv = self.csv.replace(b',en,', b',fr,')
        with self.assertRaisesRegex(ValueError, 'metadata disagreement'): self.build()

    def test_other_publisher_cannot_collide(self):
        self.csv += self.csv.splitlines()[1].replace(b'global-asp/asp-source', b'other/publisher') + b'\n'
        self.assertEqual(self.build()[0][0]['word_count'], 6)

    def test_duplicate_page_rejected(self):
        self.csv = self.csv.replace(b'together.,1,', b'together.,0,')
        with self.assertRaisesRegex(ValueError, 'duplicate pages'): self.build()

    def test_missing_page_rejected(self):
        self.csv = b'\n'.join(self.csv.splitlines()[:-1]) + b'\n'
        with self.assertRaisesRegex(ValueError, 'Missing or duplicate'): self.build()

    def test_different_words_rejected(self):
        self.csv = self.csv.replace(b'I can read.', b'I can write.')
        with self.assertRaisesRegex(ValueError, 'differs from original'): self.build()

    def test_author_mismatch_rejected(self):
        self.originals = {key: value.replace(b'Example Writer', b'Another Writer') for key, value in self.originals.items()}
        with self.assertRaisesRegex(ValueError, 'attribution mismatch'): self.build()

    def test_revision_must_be_pinned(self):
        self.config['dataset']['revision'] = 'main'
        with self.assertRaisesRegex(ValueError, 'immutable commit'): self.build()

    def test_word_count_mismatch_rejected(self):
        self.config['books'][0]['word_count'] = 7
        with self.assertRaisesRegex(ValueError, 'word count'): self.build()

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for path in ('../outside', '/absolute', 'a\\b', 'a%2fb', 'https://example.org', '\x00'):
                with self.subTest(path=path), self.assertRaises(ValueError): reader.safe_path(pathlib.Path(directory), path)

    def test_slug_traversal_rejected(self):
        self.config['books'][0]['slug'] = '../outside'
        with self.assertRaisesRegex(ValueError, 'slug'): self.build()

    def test_duplicate_selection_rejected(self):
        self.config['books'].append(copy.deepcopy(self.config['books'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate'): self.build()

    def test_punctuated_source_filename_allowed(self):
        old, new = '0001_test-reader.md', '0001_test.reader.md'
        self.config['books'][0]['filename'] = new
        self.csv = self.csv.replace(old.encode(), new.encode())
        self.originals[new] = self.originals.pop(old)
        self.assertEqual(len(self.build()[0]), 1)

    def test_source_filename_traversal_rejected(self):
        for filename in ('0001_../reader.md', '0001_test..reader.md', '0001_/reader.md'):
            with self.subTest(filename=filename):
                self.config['books'][0]['filename'] = filename
                with self.assertRaisesRegex(ValueError, 'source filename'): self.build()

    def test_source_story_id_mismatch_rejected(self):
        self.config['books'][0]['parallel_id'] = 'asp_0002'
        with self.assertRaisesRegex(ValueError, 'story ID'): self.build()

    def test_stable_id_mismatch_rejected(self):
        self.config['books'][0]['legacy_id'] = 800002
        with self.assertRaisesRegex(ValueError, 'stable ID'): self.build()

    def test_unknown_practice_band_rejected(self):
        self.config['books'][0]['practice_band'] = 'certified-A1'
        with self.assertRaisesRegex(ValueError, 'practice band'): self.build()

    def test_duplicate_story_text_rejected(self):
        other = copy.deepcopy(self.config['books'][0])
        other.update(slug='asp-other-reader', legacy_id=800002, chapter_legacy_id=800002,
                     parallel_id='asp_0002', filename='0002_other-reader.md')
        self.config['books'].append(other)
        self.csv += b'\n'.join(self.csv.splitlines()[1:]).replace(b'asp_0001', b'asp_0002').replace(b'0001_test-reader.md', b'0002_other-reader.md') + b'\n'
        self.index += self.index.replace(b'0001', b'0002')
        self.originals['0002_other-reader.md'] = self.originals['0001_test-reader.md']
        with self.assertRaisesRegex(ValueError, 'Duplicate story text'): self.build()

    def test_selection_expansion_preserves_existing_book(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.make_repo(root)
            books, outputs = self.build()
            for relative, data in reader.make_plan(root, self.config, books, outputs).items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            second = copy.deepcopy(books[0])
            second.update(id='book:800002', legacy_id=800002)
            second['chapters'][0].update(id='chapter:800002', legacy_id=800002, book_id=800002)
            plan = reader.make_plan(root, self.config, books + [second], outputs)
            catalog = json.loads(plan['catalogs/books.json'])
            self.assertEqual(catalog[0], books[0])
            self.assertEqual([b['id'] for b in catalog], ['book:800001', 'book:800002'])
            self.assertEqual(json.loads(plan['profiles/default.json'])['books'], ['book:800001', 'book:800002'])

    def test_cover_escapes_xml(self):
        book = self.config['books'][0]
        book['title'] = '<script>alert(1)</script>'
        result = reader.cover(book)
        self.assertNotIn(b'<script>', result)
        self.assertIn(b'&lt;script&gt;', result)

    def test_corrupt_cache_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = pathlib.Path(directory)
            (cache / ('f' * 64)).write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError, 'Invalid cached'): reader.download('https://unused.invalid', 'f' * 64, cache, True, 100)

    def test_offline_missing_cache_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'Missing cached'): reader.download('https://unused.invalid', 'f' * 64, pathlib.Path(directory), True, 100)

    def make_repo(self, root):
        for directory in ('catalogs', 'profiles'):
            (root / directory).mkdir()
        values = {'catalogs/books.json': [], 'catalogs/summary.json': {'books': 0, 'chapters': 0, 'preserved_count': 19},
                  'profiles/default.json': {'books': [], 'files': ['catalogs/books.json'], 'payload_bytes': 3},
                  'manifest.json': {'schema_version': 1, 'revision': 'old', 'source_application_commit': 'preserved', 'files': [], 'counts': {}}}
        for relative, value in values.items(): (root / relative).write_bytes(reader.json_bytes(value))

    def test_plan_idempotence_and_preserved_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.make_repo(root)
            books, outputs = self.build()
            plan = reader.make_plan(root, self.config, books, outputs)
            for relative, data in plan.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            self.assertEqual(reader.make_plan(root, self.config, books, outputs), plan)
            manifest = json.loads(plan['manifest.json'])
            self.assertEqual(manifest['source_application_commit'], 'preserved')
            self.assertEqual(manifest['counts']['preserved_count'], 19)

    def test_unrelated_file_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.make_repo(root)
            books, outputs = self.build()
            path = root / 'books/asp-test-reader/chapters/001.txt'
            path.parent.mkdir(parents=True)
            path.write_text('User work')
            with self.assertRaisesRegex(ValueError, 'Refusing to overwrite'): reader.make_plan(root, self.config, books, outputs)

    def test_local_edits_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.make_repo(root)
            books, outputs = self.build()
            for relative, data in reader.make_plan(root, self.config, books, outputs).items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            (root / 'books/asp-test-reader/chapters/001.txt').write_text('User work')
            with self.assertRaisesRegex(ValueError, 'Locally edited'): reader.make_plan(root, self.config, books, outputs)

    def test_id_collision_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.make_repo(root)
            books, outputs = self.build()
            unrelated = copy.deepcopy(books[0])
            unrelated.pop('source')
            (root / 'catalogs/books.json').write_bytes(reader.json_bytes([unrelated]))
            with self.assertRaisesRegex(ValueError, 'Book ID collision'): reader.make_plan(root, self.config, books, outputs)


    def test_application_credit_fields(self):
        chapter = self.build()[0][0]['chapters'][0]
        for key in ('license_url', 'license_label', 'source_url', 'attribution', 'adaptation_note'):
            self.assertTrue(chapter[key])
        self.assertIn('Example Writer', chapter['attribution'])
        # Collection loader currently discards adaptation_note, so credit includes it too.
        self.assertIn(reader.CHANGES, chapter['attribution'])

    def test_additional_publisher_credit_preserved(self):
        notice = {"text": "© Example Author, Designer and Publisher 2015", "evidence_url": "https://example.org/credits"}
        self.config['books'][0]['additional_attribution'] = [notice]
        books, files = self.build()
        source = json.loads(files['books/asp-test-reader/source.json'])
        self.assertEqual(source['additional_attribution'], [notice])
        for value in (notice['text'], notice['evidence_url']):
            self.assertIn(value, books[0]['chapters'][0]['attribution'])
            self.assertIn(value, files['books/asp-test-reader/LICENSE.md'].decode())
        self.assertEqual(books[0]['author'], 'Example Writer')
        self.assertEqual(source['license']['id'], 'CC-BY-3.0')

    def test_missing_publisher_credit_evidence_rejected(self):
        self.config['books'][0]['additional_attribution'] = [{"text": "Publisher credit"}]
        with self.assertRaisesRegex(ValueError, 'publisher notice evidence'): self.build()

    def test_translation_alias_preserved(self):
        self.originals['0001_test-reader.md'] += b'* Translation: Another Translator\n'
        books, files = self.build()
        source = json.loads(files['books/asp-test-reader/source.json'])
        self.assertEqual(source['translator'], 'Another Translator')
        self.assertIn('Translation: Another Translator.', books[0]['chapters'][0]['attribution'])

    def test_all_contributor_roles_preserved(self):
        key = '0001_test-reader.md'
        self.originals[key] += b'* Adaptation: Example Adapter\n* Translated By: Example Translator\n* Illustration: Example Illustrator\n'
        books, files = self.build()
        source = json.loads(files['books/asp-test-reader/source.json'])
        self.assertEqual(source['adaptation'], 'Example Adapter')
        self.assertEqual(source['translator'], 'Example Translator')
        self.assertEqual(source['original_illustrator'], 'Example Illustrator')
        for name in ('Example Adapter', 'Example Translator', 'Example Illustrator'):
            self.assertIn(name, books[0]['chapters'][0]['attribution'])
            self.assertIn(name.encode(), files['books/asp-test-reader/LICENSE.md'])

    def test_unexpected_local_files_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.make_repo(root)
            books, outputs = self.build()
            for filename in ('interrupted.tmp', 'private-note.txt'):
                (root / filename).write_text('Not a resource')
                with self.subTest(filename=filename), self.assertRaisesRegex(ValueError, 'Unexpected local files'):
                    reader.make_plan(root, self.config, books, outputs)
                (root / filename).unlink()

    def test_dangling_symlink_not_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            root = base / 'repo'
            root.mkdir()
            self.make_repo(root)
            outside = base / 'outside'
            (root / 'interrupted.tmp').symlink_to(outside)
            books, outputs = self.build()
            with self.assertRaisesRegex(ValueError, 'Unexpected local files'):
                reader.make_plan(root, self.config, books, outputs)
            self.assertFalse(outside.exists())

    def test_write_failure_rolls_back_all_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / 'repo'
            root.mkdir()
            (root / 'catalog.json').write_bytes(b'old catalog')
            (root / 'manifest.json').write_bytes(b'old manifest')
            plan = {'a-new.txt': b'new story', 'catalog.json': b'new catalog', 'manifest.json': b'new manifest'}
            calls = []
            def fail_on_manifest(source, target):
                calls.append(target.name)
                if target.name == 'manifest.json': raise OSError('Simulated disk failure')
                source.replace(target)
            with self.assertRaisesRegex(OSError, 'Simulated disk failure'):
                reader.apply_plan(root, plan, list(plan), replace=fail_on_manifest)
            self.assertEqual(calls[-1], 'manifest.json')
            self.assertEqual((root / 'catalog.json').read_bytes(), b'old catalog')
            self.assertEqual((root / 'manifest.json').read_bytes(), b'old manifest')
            self.assertFalse((root / 'a-new.txt').exists())
            self.assertFalse(reader.transaction_directory(root).exists())

    def test_keyboard_interrupt_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / 'repo'
            root.mkdir()
            (root / 'a.txt').write_bytes(b'old')
            plan = {'a.txt': b'new', 'b.txt': b'added'}
            def interrupt_second(source, target):
                if target.name == 'b.txt': raise KeyboardInterrupt()
                source.replace(target)
            with self.assertRaises(KeyboardInterrupt):
                reader.apply_plan(root, plan, list(plan), replace=interrupt_second)
            self.assertEqual((root / 'a.txt').read_bytes(), b'old')
            self.assertFalse((root / 'b.txt').exists())

    def test_interrupted_transaction_can_be_recovered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / 'repo'
            root.mkdir()
            (root / 'a.txt').write_bytes(b'new')
            transaction = reader.transaction_directory(root)
            (transaction / 'old').mkdir(parents=True)
            (transaction / 'old/a.txt').write_bytes(b'old')
            reader.save_journal(transaction, {'root': str(root.resolve()), 'phase': 'committing', 'files': [{'path': 'a.txt', 'old_sha256': reader.sha256(b'old'), 'new_sha256': reader.sha256(b'new')}]})
            reader.recover_transaction(root)
            self.assertEqual((root / 'a.txt').read_bytes(), b'old')
            self.assertFalse(transaction.exists())

    def test_recovery_refuses_new_user_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / 'repo'
            root.mkdir()
            (root / 'a.txt').write_bytes(b'user edit')
            transaction = reader.transaction_directory(root)
            (transaction / 'old').mkdir(parents=True)
            (transaction / 'old/a.txt').write_bytes(b'old')
            reader.save_journal(transaction, {'root': str(root.resolve()), 'phase': 'committing', 'files': [{'path': 'a.txt', 'old_sha256': reader.sha256(b'old'), 'new_sha256': reader.sha256(b'new')}]})
            with self.assertRaisesRegex(ValueError, 'changed after interruption'):
                reader.recover_transaction(root)
            self.assertEqual((root / 'a.txt').read_bytes(), b'user edit')

    def test_dangling_recovery_temporary_cannot_write_outside(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            root = base / 'repo'
            root.mkdir()
            (root / 'a.txt').write_bytes(b'new')
            outside = base / 'outside'
            (root / 'a.txt.hf-restore.tmp').symlink_to(outside)
            transaction = reader.transaction_directory(root)
            (transaction / 'old').mkdir(parents=True)
            (transaction / 'old/a.txt').write_bytes(b'old')
            reader.save_journal(transaction, {'root': str(root.resolve()), 'phase': 'committing', 'files': [{'path': 'a.txt', 'old_sha256': reader.sha256(b'old'), 'new_sha256': reader.sha256(b'new')}]})
            with self.assertRaises(FileExistsError): reader.recover_transaction(root)
            self.assertFalse(outside.exists())
            self.assertEqual((root / 'a.txt').read_bytes(), b'new')

    def test_successful_transaction_cleans_backups(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / 'repo'
            root.mkdir()
            plan = {'story.txt': b'new', 'manifest.json': b'new manifest'}
            reader.apply_plan(root, plan, list(plan))
            self.assertEqual((root / 'story.txt').read_bytes(), b'new')
            self.assertFalse(reader.transaction_directory(root).exists())


    def test_chapter_id_collision_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.make_repo(root)
            books, outputs = self.build()
            unrelated = copy.deepcopy(books[0])
            unrelated.pop('source')
            unrelated['id'] = 'book:22'
            unrelated['legacy_id'] = 22
            (root / 'catalogs/books.json').write_bytes(reader.json_bytes([unrelated]))
            with self.assertRaisesRegex(ValueError, 'Chapter ID collision'):
                reader.make_plan(root, self.config, books, outputs)

    def test_dangling_cache_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = pathlib.Path(directory)
            outside = cache / 'outside'
            (cache / ('f' * 64)).symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'Symlinked cache'):
                reader.download('https://unused.invalid', 'f' * 64, cache, True, 100)
            self.assertFalse(outside.exists())


if __name__ == '__main__':
    unittest.main()
