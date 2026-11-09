"""Offline anthology, byte preservation and compatibility contract tests."""
import copy
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import import_hf_readers as reader
import story_anthology as anthology


class StoryAnthologyTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'tools/story_anthology.json').read_text())
        self.public = json.loads((ROOT / 'catalogs/books.json').read_text())
        self.archive = json.loads((ROOT / self.config['archive_path']).read_text())
        self.titles = json.loads((ROOT / 'tools/book_titles.json').read_text())['books']
        self.book = next(b for b in self.public if b['id'] == self.config['id'])
        self.sources = [b for b in self.public if b['id'] != self.config['id']] + self.archive
        self.selected_archive = [b for b in self.archive if b['id'] in {c['source_book_id'] for c in self.book['chapters']}]

    def build(self):
        return anthology.build(ROOT, self.config, self.sources, self.titles, {})

    def test_public_catalog_has_three_books_and_sixty_four_story_anthology(self):
        original = [b for b in self.public if b['id'] in {'book:1', 'book:7', 'book:157', 'book:810000'}]
        self.assertEqual([b['id'] for b in original], ['book:1', 'book:7', 'book:157', 'book:810000'])
        self.assertEqual([b['chapter_count'] for b in original], [5, 14, 7, 64])
        self.assertEqual(len(self.archive), 100)
        self.assertTrue(all(b['chapter_count'] == 1 for b in self.archive))
        self.assertTrue(all(c['word_count'] >= 100 for c in self.book['chapters']))
        selected_slugs = {pathlib.PurePosixPath(b['source']['path']).parts[1] for b in self.selected_archive}
        self.assertFalse(selected_slugs & set(self.config['exclude_slugs']))
        profile = json.loads((ROOT / 'profiles/default.json').read_text())
        self.assertEqual(profile['books'], [b['id'] for b in self.public])
        self.assertFalse(set(profile['books']) & {b['id'] for b in self.archive})

    def test_generated_catalog_and_files_are_current(self):
        books, files = self.build()
        self.assertEqual([{k:v for k,v in b.items() if k != 'revision'} for b in books],
                         [{k:v for k,v in b.items() if k != 'revision'} for b in self.public])
        for path, data in files.items():
            self.assertEqual((ROOT / path).read_bytes(), data, path)

    def test_one_to_one_mapping_keeps_exact_body_refs_and_credits(self):
        source = {b['id']: b for b in self.archive}
        mapping = json.loads((ROOT / self.config['mapping_path']).read_text())['items']
        self.assertEqual(len(mapping), 64)
        self.assertEqual({m['source_book_id'] for m in mapping}, {b['id'] for b in self.selected_archive})
        self.assertEqual(len({m['chapter_id'] for m in mapping}), 64)
        for chapter, entry in zip(self.book['chapters'], mapping):
            old = source[entry['source_book_id']]
            original = old['chapters'][0]
            self.assertEqual(chapter['body'], original['body'])
            self.assertEqual(chapter['body'], entry['body'])
            self.assertEqual(chapter['author'], old['author'])
            self.assertEqual(chapter['title_i18n'], old['title_i18n'])
            for field in ('title', 'source_url', 'license_url', 'license_label', 'attribution', 'adaptation_note'):
                self.assertEqual(chapter[field], original[field])
            self.assertEqual(chapter['legacy_id'], original['legacy_id'] + self.config['chapter_id_offset'])
            credits = (ROOT / 'books/childrens-short-stories/LICENSE.md').read_text()
            self.assertIn('per-story credits', credits)
            self.assertIn(f'## {chapter["chapter_number"]}. {chapter["title"]}', credits)
            self.assertNotIn('http', self.book['description'])
            self.assertNotIn(chapter['attribution'], self.book['description'])
            self.assertLess(len(self.book['description']), 200)
            self.assertEqual(reader.sha256((ROOT / chapter['body']['path']).read_bytes()), chapter['body']['sha256'])

    def test_no_story_body_copies_and_short_to_long_order(self):
        _, files = self.build()
        self.assertFalse(any('/chapters/' in path for path in files))
        self.assertEqual(len({c['body']['path'] for c in self.book['chapters']}), 64)
        lengths = [c['word_count'] for c in self.book['chapters']]
        self.assertEqual(lengths, sorted(lengths))
        self.assertEqual([c['chapter_number'] for c in self.book['chapters']], list(range(1, 65)))
        self.assertEqual(self.book['word_count'], sum(lengths))
        source = json.loads(files['books/childrens-short-stories/source.json'])
        self.assertEqual(source['new_body_bytes'], 0)
        self.assertEqual(source['reused_body_bytes'], sum(c['body']['bytes'] for c in self.book['chapters']))

    def test_all_original_ids_remain_resolvable_in_archive(self):
        combined = anthology.preserved_books(ROOT, self.public, self.config)
        self.assertEqual(len(combined), len(self.public) + 100)
        self.assertEqual(len({b['id'] for b in combined}), len(self.public) + 100)
        old_chapters = {c['id'] for b in self.archive for c in b['chapters']}
        self.assertFalse(old_chapters & {c['id'] for c in self.book['chapters']})

    def test_corrupt_body_reference_rejected(self):
        target = self.selected_archive[0]
        target['chapters'][0]['body']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            self.build()

    def test_duplicate_body_rejected(self):
        target1 = self.selected_archive[1]
        target0 = self.selected_archive[0]
        target1['chapters'][0]['body'] = copy.deepcopy(target0['chapters'][0]['body'])
        target1['word_count'] = target0['word_count']
        with self.assertRaisesRegex(ValueError, 'Duplicate anthology'):
            self.build()

    def test_multiple_chapter_source_rejected(self):
        self.archive[0]['chapter_count'] = 2
        with self.assertRaisesRegex(ValueError, 'single-chapter'):
            self.build()

    def test_missing_attribution_and_license_change_rejected(self):
        target = self.selected_archive[0]
        for key, value in (('attribution', ''), ('license_url', 'https://example.com/wrong')):
            with self.subTest(key=key):
                original = target['chapters'][0][key]
                target['chapters'][0][key] = value
                with self.assertRaises(ValueError): self.build()
                target['chapters'][0][key] = original

    def test_chapter_id_collision_rejected(self):
        self.config['chapter_id_offset'] = 0
        with self.assertRaisesRegex(ValueError, 'chapter ID collision'):
            self.build()

    def test_public_archive_overlap_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate public/archive'):
            anthology.preserved_books(ROOT, self.public + [self.archive[0]], self.config)

    def test_rebuild_is_idempotent_and_does_not_relist_standalone_books(self):
        config = json.loads((ROOT / 'tools/hf_readers.json').read_text())
        # Generated original readers are unchanged inputs; this needs no network/cache.
        plan = reader.make_plan(ROOT, config, self.archive, {})
        for path, data in plan.items():
            self.assertEqual((ROOT / path).read_bytes(), data, path)
        self.assertEqual(plan, reader.make_plan(ROOT, config, self.archive, {}))
        self.assertEqual(json.loads(plan['catalogs/books.json']), self.public)


if __name__ == '__main__':
    unittest.main()
