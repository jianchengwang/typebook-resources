"""Offline publication, source-pinning and compatibility regressions."""
import copy
import hashlib
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import import_gutenberg_readers as reader

class GutenbergReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads((ROOT/'tools/gutenberg_readers.json').read_text())
        cls.public=json.loads((ROOT/'catalogs/books.json').read_text())

    def test_reviewed_configuration_and_unique_books(self):
        reader.validate_config(self.config)
        self.assertEqual(len(self.config['books']),96)
        self.assertEqual(len(self.public),100)
        self.assertEqual(len({b['title'] for b in self.config['books']}),96)

    def test_unreviewed_entries_and_foreign_original_rejected(self):
        for branch,key,value in [('rights','reviewed',False),('completeness','reviewed',False),
                                  ('rights','source_status','unknown'),('rights','author_death_year',2000)]:
            c=copy.deepcopy(self.config);c['books'][0][branch][key]=value
            with self.subTest(branch=branch,key=key),self.assertRaises(ValueError): reader.validate_config(c)
        c=copy.deepcopy(self.config);c['books'][0]['original_language']='fr'
        with self.assertRaises(ValueError): reader.validate_config(c)

    def test_invalid_pins_and_paths_rejected(self):
        for key,value in [('text_sha256','x'*64),('slug','../../private'),('gutenberg_id',True),('text_url','https://example.com/book')]:
            c=copy.deepcopy(self.config);c['books'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): reader.validate_config(c)

    def test_duplicate_editions_and_folders_rejected(self):
        for key in ['gutenberg_id','slug']:
            c=copy.deepcopy(self.config);c['books'][1][key]=c['books'][0][key]
            with self.assertRaises(ValueError): reader.validate_config(c)

    def test_all_new_books_have_real_multiple_sections_and_credits(self):
        books=[b for b in self.public if b.get('source',{}).get('import_id')==reader.IMPORT_ID]
        self.assertEqual(len(books),96)
        for book in books:
            self.assertGreaterEqual(book['chapter_count'],2)
            self.assertEqual(book['word_count'],sum(c['word_count'] for c in book['chapters']))
            self.assertEqual(set(book['title_i18n']),{'en','zh-CN','ja'})
            self.assertTrue(book['practice']['not_cefr_tested'])
            self.assertEqual(book['license_status'],'verified-public-domain-us')
            for c in book['chapters']:
                self.assertIn('gutenberg.org',c['source_url'])
                self.assertTrue(c['attribution'])
                self.assertIn('USA',c['license_label'])

    def test_stable_original_books_and_compatibility_preserved(self):
        byid={b['id']:b for b in self.public}
        self.assertEqual([byid[x]['chapter_count'] for x in ['book:1','book:7','book:157','book:810000']],[5,14,7,64])
        archive=json.loads((ROOT/'catalogs/standalone-readers.json').read_text())
        self.assertEqual(len(archive),100)
        self.assertFalse({b['id'] for b in archive}&set(byid))
        self.assertEqual(self.public[-1]['id'],'book:810000')
        expected={'book:1':'df260fc9fd977724b425ead5c81df914224409e56c132b5707d476896a260e3e',
                  'book:7':'519d303f2df1a4b99997d5a3ecd5e471e36a2c5b29e46bcbd6ee1b94f0d69b9c',
                  'book:157':'561345370dc7af9c1427a0bef5e97590e74ef42ae1720df54fa151cb0796798c',
                  'book:810000':'3f6f07871134037acca7db23ad3944f153b9d1fe82e801e74137a32db6d4a8a7'}
        for id,digest in expected.items():
            self.assertEqual(hashlib.sha256(json.dumps(byid[id],sort_keys=True,ensure_ascii=False).encode()).hexdigest(),digest)

    def test_sources_are_hash_pinned(self):
        for b in self.config['books']:
            for suffix in ['.html','.page.html']: reader.source_bytes(ROOT,None,b,suffix)
        b=copy.deepcopy(self.config['books'][0]);b['text_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Pinned source mismatch'): reader.source_bytes(ROOT,None,b,'.html')

    def test_wrong_counts_rejected(self):
        b=copy.deepcopy(self.config['books'][0]);b['completeness']['word_count']+=1
        with self.assertRaisesRegex(ValueError,'Word count mismatch'): reader.build_book(ROOT,None,b)
        b=copy.deepcopy(self.config['books'][0]);b['completeness']['section_count']+=1
        with self.assertRaisesRegex(ValueError,'Section count mismatch'): reader.build_book(ROOT,None,b)

    def test_atomic_plan_reproduces_repository(self):
        plan=reader.make_plan(ROOT,self.config)
        for path,data in plan.items(): self.assertEqual((ROOT/path).read_bytes(),data,path)

    def test_narrative_framing_and_complex_source_regressions(self):
        needles={12:'Child of the pure unclouded brow',316:'Once upon a time we all walked on the golden road',
                 1837:'I will set down a tale',1557:'father of the boy hero',2865:'Poor little Otto',
                 10745:'Now this child, Launcelot',19360:'Eleanor and I are subject to fads',
                 20651:'This story is told by Will Gordon',897:'Miss Bunch',421:'I will begin the story of my adventures'}
        books={b.get('source',{}).get('gutenberg_id'):b for b in self.public}
        for id,needle in needles.items():
            text=' '.join((ROOT/c['body']['path']).read_text() for c in books[id]['chapters'])
            self.assertIn(needle,text,id)
        self.assertEqual(books[514]['chapter_count'],47)
        self.assertEqual(books[496]['chapter_count'],10)
        self.assertEqual(books[30494]['chapter_count'],6)
        self.assertEqual(books[961]['chapter_count'],24)
        self.assertNotIn(1480,books)
        self.assertNotIn(32224,books)

    def test_typographic_cover_escapes_markup(self):
        svg=reader.cover('<Book & title>','Author <script>',20000).decode()
        self.assertNotIn('<script>',svg);self.assertIn('&lt;Book &amp; title&gt;',svg)
        self.assertIn('ENGLISH ORIGINAL READERS',svg)

    def test_generated_markdown_uses_lf_for_git_hash_stability(self):
        self.assertNotIn('\r',reader.plaintext('<p>A\r\nB\rC</p>'))
        for b in self.config['books']:
            self.assertNotIn(b'\r',(ROOT/'books'/b['slug']/'LICENSE.md').read_bytes())

    def test_sources_not_bundled_but_practice_and_licenses_are(self):
        profile=json.loads((ROOT/'profiles/default.json').read_text())
        for b in self.config['books']:
            folder='books/'+b['slug']
            self.assertNotIn(folder+'/original.html',profile['files'])
            self.assertNotIn(folder+'/catalog.html',profile['files'])
            self.assertIn(folder+'/LICENSE.md',profile['files'])
            self.assertIn(folder+'/source.json',profile['files'])
        self.assertEqual(profile['books'],[b['id'] for b in self.public])

if __name__=='__main__': unittest.main()
