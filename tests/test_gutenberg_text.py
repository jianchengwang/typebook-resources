import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'tools'))
from gutenberg_text import ExtractionError, extract_book


START = '<p>*** START OF THE PROJECT GUTENBERG EBOOK TEST ***</p>'
END = '<p>*** END OF THE PROJECT GUTENBERG EBOOK TEST ***</p>'


def page(body):
    return '<!DOCTYPE html><html><head><title>Ignored</title></head><body>' + START + body + END + '</body></html>'


class GutenbergTests(unittest.TestCase):
    def test_basic_chapters_and_unicode(self):
        result = extract_book(page('<h1>Book title</h1><h2 id="c1">CHAPTER I</h2><p>“Hello,” said the child. A &amp; B.</p><h2 id="c2">CHAPTER II</h2><p>Last scene. The end.</p>'))
        self.assertEqual(len(result['chapters']), 2)
        self.assertIn('“Hello,” said the child. A & B.', result['chapters'][0]['text'])
        self.assertTrue(result['diagnostics']['reconstruction_verified'])
        self.assertNotIn('Book title', result['chapters'][0]['text'])

    def test_modern_header_footer_containers(self):
        html = '<html><body><section id="pg-header">' + START + '</section><h2>Chapter 1</h2><p>Story one.</p><h2>Chapter 2</h2><p>Story two.</p><section id="pg-footer">' + END + '<p>License.</p></section></body></html>'
        result = extract_book(html)
        self.assertEqual(len(result['chapters']), 2)
        self.assertNotIn('License', result['chapters'][-1]['text'])

    def test_explicit_anchor_inside_heading(self):
        result = extract_book(page('<h2>Contents</h2><p>Chapter list</p><h2><a id="first"></a>A Beginning</h2><p>Hello world.</p><h2><a id="last"></a>An Ending</h2><p>Goodbye world.</p>'), chapter_ids=['first', 'last'])
        self.assertEqual(result['chapters'][0]['title'], 'A Beginning')
        self.assertNotIn('Chapter list', result['chapters'][0]['text'])

    def test_verse_and_inline_words(self):
        result = extract_book(page('<h2>Chapter I</h2><p>A <em>very</em> good day.</p><div class="stanza">One line<br/>Two lines</div><h2>Chapter II</h2><p>The ending.</p>'))
        self.assertIn('A very good day.', result['chapters'][0]['text'])
        self.assertIn('One line\nTwo lines', result['chapters'][0]['text'])

    def test_nested_body_blocks_preserve_quote(self):
        result = extract_book(page('<div class="chapter"><h2>Chapter I</h2><blockquote><p>A quoted letter.</p></blockquote><p>And narration.</p></div><div class="chapter"><h2>Chapter II</h2><p>End.</p></div>'))
        self.assertIn('A quoted letter.', result['chapters'][0]['text'])
        self.assertEqual(result['chapters'][0]['text'].count('A quoted letter.'), 1)

    def test_toc_and_caption_exclusion(self):
        result = extract_book(page('<h2>Contents</h2><table><tr><td>I</td><td>II</td></tr></table><h2 id="a">Chapter I</h2><p>Story.</p><div class="figcenter"><img src="x"/><p>Caption</p></div><h2 id="b">Chapter II</h2><p>End.</p>'))
        text = ''.join(c['text'] for c in result['chapters'])
        self.assertNotIn('Caption', text)
        self.assertNotIn('Contents', text)
        self.assertEqual(len(result['chapters']), 2)

    def test_bounds_and_explicit_exclusion(self):
        result = extract_book(page('<h2 id="a">Chapter I</h2><p>Story.</p><div id="publisher"><p>Publisher advert.</p></div><h2 id="b">Chapter II</h2><p>End.</p><h2 id="notes">Publisher Notes</h2><p>Not story.</p>'), chapter_ids=['a', 'b'], end_id='notes', exclude_ids=['publisher'])
        self.assertNotIn('Publisher', ''.join(c['text'] for c in result['chapters']))

    def test_markers_required_without_both_bounds(self):
        with self.assertRaisesRegex(ExtractionError, 'marker'):
            extract_book('<html><body><h2>Chapter I</h2><p>Incomplete</p></body></html>')

    def test_missing_duplicate_reversed_anchors_rejected(self):
        html = page('<h2 id="a">One</h2><p>Story.</p><h2 id="b">Two</h2><p>End.</p>')
        for anchors in [['a', 'missing'], ['a', 'a'], ['b', 'a']]:
            with self.subTest(anchors=anchors), self.assertRaises(ExtractionError):
                extract_book(html, chapter_ids=anchors)

    def test_h3_under_part(self):
        result = extract_book(page('<h2>Part One</h2><h3>Chapter I</h3><p>First.</p><h3>Chapter II</h3><p>Second.</p>'))
        self.assertEqual(result['diagnostics']['heading_level'], 'mixed-chapter-headings')
        self.assertEqual(len(result['chapters']), 2)

    def test_mixed_heading_levels_do_not_drop_first_chapter(self):
        result = extract_book(page('<h2>CHAPTER 1 First</h2><p>First narrative.</p><h3>CHAPTER 2 Second</h3><p>Second narrative.</p>'))
        self.assertEqual(len(result['chapters']), 2)
        self.assertIn('First narrative.', result['chapters'][0]['text'])

    def test_numbers_with_separate_titles_and_in_story_signs(self):
        result = extract_book(page('<h2>Contents</h2><h3>1</h3><h3>A start</h3><p>Story.</p><h3>KEEP OUT</h3><p>More story.</p><h3>2</h3><h3>The end</h3><p>End.</p>'))
        self.assertEqual(len(result['chapters']), 2)
        self.assertEqual(result['chapters'][0]['title'], '1 — A start')
        self.assertIn('KEEP OUT', result['chapters'][0]['text'])

    def test_explicit_text_bounds_and_pattern(self):
        result = extract_book(page('<h2>Chapter 1</h2><p>Story.</p><h2>Chapter 2</h2><p>End.</p><h4>Other books</h4><p>Ad.</p>'), end_text='Other books', heading_pattern=r'^Chapter')
        self.assertEqual(len(result['chapters']), 2)
        self.assertNotIn('Other books', result['chapters'][-1]['text'])

    def test_inline_page_number_is_not_prose(self):
        result = extract_book(page('<h2>Chapter I</h2><p>A <span class="pagenum">[213]</span> good story <a href="#fn1">[1]</a>.</p><h2>Chapter II</h2><p id="fn1">[1] An author note.</p>'))
        text = ''.join(c['text'] for c in result['chapters'])
        self.assertNotIn('[213]', text)
        self.assertIn('[1] An author note.', text)

    def test_image_initials_are_restored_without_guessing(self):
        result = extract_book(page('<h2>Chapter I</h2><div class="figleft"><img alt="I"/></div><p>will tell a tale.</p><h2>Chapter II</h2><div class="figleft"><img alt="T"/></div><p>HE next day.</p>'))
        self.assertIn('I will tell a tale.', result['chapters'][0]['text'])
        self.assertIn('THE next day.', result['chapters'][1]['text'])

    def test_extra_prologue_heading_is_retained(self):
        result = extract_book(page('<h2>Prologue</h2><p>Frame narrative.</p><h3>Chapter I</h3><p>First.</p><h3>Chapter II</h3><p>End.</p>'), extra_heading_texts=['Prologue'])
        self.assertEqual(len(result['chapters']), 3)
        self.assertIn('Frame narrative.', result['chapters'][0]['text'])

    def test_repeated_advertisement_bound_requires_occurrence(self):
        html = page('<h2>Chapter I</h2><p>Story.</p><h2>Chapter II</h2><p>End.</p><h4>Ad</h4><p>First ad.</p><h4>Ad</h4><p>Second ad.</p>')
        with self.assertRaises(ExtractionError):
            extract_book(html, end_text='Ad')
        result = extract_book(html, end_text='Ad', end_text_occurrence=1)
        self.assertNotIn('First ad.', result['chapters'][-1]['text'])

    def test_image_heading_alt_is_preserved_but_not_duplicated(self):
        result = extract_book(page('<h2><img alt="Prologue."/></h2><p>Frame narrative.</p><h3>Chapter I<img alt="Chapter I"/></h3><p>First.</p><h3>Chapter II</h3><p>End.</p>'), extra_heading_texts=['Prologue.'])
        self.assertEqual(result['chapters'][0]['title'], 'Prologue.')
        self.assertEqual(result['chapters'][1]['title'], 'Chapter I')

    def test_explicit_paragraph_chapter_texts(self):
        result = extract_book(page('<p>Front matter</p><p>Adventure First</p><p>First story.</p><p>Adventure Second</p><p>Last story.</p>'), chapter_texts=['Adventure First', 'Adventure Second'])
        self.assertEqual(len(result['chapters']), 2)
        self.assertNotIn('Front matter', result['chapters'][0]['text'])

    def test_dropcap_does_not_attach_to_epigraph(self):
        result = extract_book(page('<h2>Chapter I</h2><div class="figleft"><img alt="T"/></div><p>"An epigraph."</p><div class="unindent">HE story starts.</div><h2>Chapter II</h2><p>End.</p>'))
        self.assertIn('THE story starts.', result['chapters'][0]['text'])
        self.assertNotIn('T"An epigraph', result['chapters'][0]['text'])

    def test_duplicate_chapter_text_rejected(self):
        with self.assertRaisesRegex(ExtractionError, 'Duplicate chapter'):
            extract_book(page('<h2>Same</h2><p>Same story</p><h2>Same</h2><p>Same story</p>'))

    def test_prefatory_exact_source_and_reconstruction(self):
        html = page('<p>A literary opening.</p><h2>Chapter I</h2><p>First.</p><h2>Chapter II</h2><p>Last.</p>')
        result = extract_book(html, prefatory_sections=[{'title': 'Opening', 'text': 'A literary opening.'}])
        self.assertEqual(result['chapters'][0]['text'], 'A literary opening.\n')
        self.assertTrue(result['diagnostics']['reconstruction_verified'])
        self.assertFalse(any(x['preview'] == 'A literary opening.' for x in result['diagnostics']['omitted']))
        with self.assertRaisesRegex(ExtractionError, 'exactly one source block'):
            extract_book(html, prefatory_sections=[{'title': 'Opening', 'text': 'Invented opening.'}])
        with self.assertRaisesRegex(ExtractionError, 'overlaps or follows'):
            extract_book(html, prefatory_sections=[{'title': 'Opening', 'text': 'Last.'}])

    def test_prefatory_source_order_required(self):
        with self.assertRaisesRegex(ExtractionError, 'source order'):
            extract_book(page('<p>Frame one.</p><p>Frame two.</p><h2>Chapter I</h2><p>First.</p><h2>Chapter II</h2><p>Last.</p>'), prefatory_sections=[{'title': 'Two', 'text': 'Frame two.'}, {'title': 'One', 'text': 'Frame one.'}])

    def test_editorial_title_does_not_change_source(self):
        result = extract_book(page('<div id="opening"><p>Original frame.</p></div><h2 id="c1">Chapter I</h2><p>First.</p>'), chapter_ids=['opening', 'c1'], chapter_titles={'opening': 'Prologue'})
        self.assertEqual(result['chapters'][0]['title'], 'Prologue')
        self.assertEqual(result['chapters'][0]['text'], 'Original frame.\n')
        self.assertTrue(result['diagnostics']['reconstruction_verified'])

    def test_trailing_empty_heading_rejected(self):
        with self.assertRaisesRegex(ExtractionError, 'Trailing heading'):
            extract_book(page('<h2>Chapter I</h2><p>Story</p><h2>Chapter II</h2>'))


if __name__ == '__main__':
    unittest.main()
