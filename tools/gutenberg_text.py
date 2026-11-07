#!/usr/bin/env python3
"""Conservative, dependency-free chapter extraction from Gutenberg HTML.

The importer must review diagnostics and pin per-edition selectors.  This module
verifies internal extraction consistency, not completeness of a published book.
It never downloads data.  Copyright/licensing decisions belong to the importer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from html.parser import HTMLParser
import re
from typing import Optional


class ExtractionError(ValueError):
    pass


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)
    parent: Optional['Node'] = None
    order: int = 0

    @property
    def id(self):
        return self.attrs.get('id', '') or self.attrs.get('name', '')


VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
BLOCKS = {'p', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'dt', 'dd', 'tr', 'figcaption', 'address'}
CONTAINERS = {'div', 'section', 'article', 'blockquote', 'aside', 'main', 'body', 'header', 'footer'}
SKIP_TAGS = {'head', 'script', 'style', 'nav', 'noscript', 'svg', 'figure', 'figcaption'}
APPARATUS = re.compile(r'^(?:contents|table of contents|list of chapters|illustrations|list of illustrations|list of pictures|transcriber[’\x27]s? notes?|transcription notes?|copyright|title page|dedication|project gutenberg(?:.*))$', re.I)
CHAPTER = re.compile(r'^(?:(?:chapter|chap\.?|book|part|section|canto)\s+|[IVXLCDM]+(?:[.\s:—–]|$)|\d+(?:[.\s:—–]|$))', re.I)
START = re.compile(r'\*{3}\s*START OF (?:THE|THIS) PROJECT GUTENBERG', re.I)
END = re.compile(r'\*{3}\s*END OF (?:THE|THIS) PROJECT GUTENBERG', re.I)


class TreeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('root')
        self.stack = [self.root]
        self.nodes = [self.root]
        self.malformed = []

    def handle_starttag(self, tag, attrs):
        # Common optional-end-tag HTML, not XML.  Close an open paragraph/list
        # item before an adjacent peer; do not discard any text.
        if tag in {'p', 'li', 'dt', 'dd', 'tr'} and self.stack[-1].tag == tag:
            self.stack.pop()
        if tag in BLOCKS | CONTAINERS and self.stack[-1].tag == 'p':
            self.stack.pop()
        node = Node(tag, dict(attrs), parent=self.stack[-1], order=len(self.nodes))
        self.nodes.append(node)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                self.stack = self.stack[:i]
                return
        if tag not in VOID:
            self.malformed.append('unmatched closing tag: ' + tag)

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _tokens(node):
    return set((node.attrs.get('class') or '').lower().split())


def _normalize(text, preserve_lines=False):
    text = text.replace('\u00a0', ' ').replace('\u00ad', '')
    if preserve_lines:
        return '\n'.join(' '.join(line.split()) for line in text.splitlines() if line.strip()).strip()
    return ' '.join(text.split())


def _text(node, preserve_lines=False):
    def pieces(n):
        if isinstance(n, str):
            return n
        if n.tag == 'img':
            alt = (n.attrs.get('alt') or '').strip()
            heading_parent = next((p for p in _ancestors(n.parent) if p.tag in {'h1','h2','h3','h4','h5','h6'}), None)
            def without_images(x):
                if isinstance(x, str):
                    return x
                if x.tag in {'img','svg'}:
                    return ''
                return ''.join(without_images(c) for c in x.children)
            image_only_heading = heading_parent is not None and not without_images(heading_parent).strip()
            return alt if re.fullmatch(r'[A-Z]', alt) or (image_only_heading and alt and not re.search(r'\.(?:jpg|png|gif|svg)\b', alt, re.I)) else ''
        if n.tag in {'script', 'style', 'svg'} or _tokens(n) & {'pagenum', 'pagenumber'}:
            return ''
        if n.tag == 'br':
            return '\n'
        # Empty anchors add no text; visible author footnotes are retained
        # unless the importer supplies an explicit edition boundary.
        return ''.join(pieces(c) for c in n.children)
    return _normalize(pieces(node), preserve_lines)


def _ancestors(node):
    while node is not None:
        yield node
        node = node.parent


def _source_id(node):
    for n in _ancestors(node):
        if n.id:
            return n.id
    # Gutenberg often puts an empty anchor inside a heading.
    def descendant(n):
        for c in n.children:
            if isinstance(c, Node):
                if c.id:
                    return c.id
                x = descendant(c)
                if x:
                    return x
        return ''
    return descendant(node)


def _node_reason(node):
    if node.tag in SKIP_TAGS:
        return 'non-reading-element'
    if node.tag in {'h3','h4','h5','h6'} and _text(node) == 'Original' and any(isinstance(c, Node) and c.tag == 'a' and (c.attrs.get('href') or '').startswith('images/') for c in node.children):
        return 'original-image-link'
    ident = node.id.lower()
    classes = _tokens(node)
    if ident in {'pg-header', 'pg-footer', 'pgheader', 'pgfooter', 'pg-end-separator', 'pg-start-separator'} or classes & {'pgheader', 'pgfooter'}:
        return 'gutenberg-apparatus'
    if classes & {'toc', 'table-of-contents', 'contents', 'caption', 'figcaption', 'figcenter', 'figleft', 'figright', 'illustration', 'transnote', 'transcribernote', 'transcribers-note', 'pagenum', 'pagenumber'}:
        return 'navigation-or-illustration'
    if ident in {'toc', 'table-of-contents'}:
        return 'navigation-or-illustration'
    return None


def _flatten(root):
    blocks, omitted = [], []

    def append(node, text, tag=None):
        if text and re.fullmatch(r'\[Illustration(?::[^\]]*)?\]', text, re.I):
            omitted.append({'reason': 'illustration-placeholder', 'source_id': node.id, 'words': len(text.split()), 'preview': text[:100]})
            return
        if text:
            blocks.append({'text': text, 'tag': tag or node.tag, 'order': node.order,
                           'source_id': _source_id(node), 'node': node})

    def walk(node):
        if _tokens(node) & {'figleft', 'dropcap', 'drop-cap'}:
            text = _text(node)
            if re.fullmatch(r'[A-Z]', text):
                append(node, text, 'dropcap')
                return
        reason = _node_reason(node)
        if reason:
            text = _text(node)
            if text:
                omitted.append({'reason': reason, 'source_id': node.id,
                                'words': len(text.split()), 'preview': text[:100]})
            return
        if node.tag in BLOCKS:
            text = _text(node, preserve_lines=node.tag == 'pre' or bool(_tokens(node) & {'verse', 'poem', 'stanza'}))
            append(node, text)
            return
        # Poetry is often a stanza containing span.i0/line elements plus br.
        if _tokens(node) & {'stanza', 'verse'}:
            append(node, _text(node, preserve_lines=True), 'p')
            return
        pending = []
        for c in node.children:
            if isinstance(c, str):
                pending.append(c)
            elif c.tag in BLOCKS | CONTAINERS | {'table', 'tbody', 'thead', 'ul', 'ol', 'dl'} or _node_reason(c):
                append(node, _normalize(''.join(pending)), 'p')
                pending = []
                walk(c)
            else:
                # Inline HTML outside a paragraph.  Handle br explicitly so
                # verse/div-only editions retain line boundaries.
                pending.append('\n' if c.tag == 'br' else _text(c))
        append(node, _normalize(''.join(pending)), 'p')

    walk(root)
    merged = []
    for i, block in enumerate(blocks):
        if block['tag'] == 'dropcap':
            following_blocks = []
            for later in blocks[i + 1:]:
                if later['tag'] in {'h1','h2','h3','h4','h5','h6','dropcap'}:
                    break
                if later['tag'] == 'p' and not _tokens(later['node']) & {'stanza', 'verse', 'poem'}:
                    following_blocks.append(later)
            if not following_blocks:
                raise ExtractionError('Drop-cap image has no following prose paragraph')
            next_block = next((b for b in following_blocks if _tokens(b['node']) & {'unindent', 'drop-cap', 'dropcap'}), following_blocks[0])
            initial, following = block['text'], next_block['text']
            token = following.split()[0] if following else ''
            # A/I can be complete words. Other standalone initials, or uppercase
            # word remainders such as T+HE / I+T / A+ND, join without a space.
            joiner = (' ' if initial in {'A', 'I'} and not
                      (token in ({'T', 'N', 'F', 'S'} if initial == 'I' else {'ND', 'S', 'T', 'RE', 'N'})) else '')
            next_block['text'] = initial + joiner + following
        else:
            merged.append(block)
    return merged, omitted


def _anchor_order(parser, anchor):
    matches = [n for n in parser.nodes if n.id == anchor]
    if len(matches) != 1:
        raise ExtractionError(f'Expected one anchor {anchor!r}; found {len(matches)}')
    n = matches[0]
    # An empty a/span inside a heading identifies that whole heading.
    for p in _ancestors(n):
        if p.tag in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            return p.order
    return n.order


def extract_book(html, *, start_id=None, end_id=None, chapter_ids=None,
                 heading_level=None, heading_pattern=None, start_text=None, end_text=None,
                 chapter_texts=None, prefatory_sections=(), chapter_titles=None,
                 end_text_occurrence=None, extra_heading_texts=(),
                 exclude_ids=(), min_chapter_words=20):
    """Return ``{'chapters': [...], 'diagnostics': {...}}`` from an HTML edition.

    ``start_id`` is inclusive; ``end_id`` is exclusive. ``chapter_ids`` gives
    exact ordered chapter anchors and implies start_id=chapter_ids[0]. Without
    anchors the first substantial h2/h3 section is chosen conservatively.
    ``chapter_texts`` selects exact source blocks when semantic headings/IDs are
    absent. ``heading_pattern`` filters headings at an explicit level. Extra
    named headings retain narrative prologues/conclusions. Text bounds are exact;
    a repeated end label needs an explicit one-based ``end_text_occurrence``.
    ``prefatory_sections`` restores exact single source blocks before the main
    narrative. ``chapter_titles`` maps selected source IDs to editorial display
    titles only, without changing their source text.
    Warnings require editorial review; they are never silently treated as proof
    of completeness. Gutenberg markers are required unless both bounds supplied.
    """
    original_bytes = html if isinstance(html, bytes) else html.encode('utf-8') if isinstance(html, str) else b''
    if isinstance(html, bytes):
        html = html.decode('utf-8-sig', errors='strict')
    if not isinstance(html, str) or not html.strip():
        raise ExtractionError('Missing HTML')
    parser = TreeParser()
    parser.feed(html)
    parser.close()
    nodes = parser.nodes
    bodies = [n for n in nodes if n.tag == 'body']
    if len(bodies) != 1:
        raise ExtractionError('Expected one HTML body')
    raw_text = _text(bodies[0])
    if not (START.search(raw_text) and END.search(raw_text)) and not (start_id and end_id):
        raise ExtractionError('Missing Gutenberg start/end marker; explicit bounds required')
    blocks, omitted = _flatten(bodies[0])
    if not blocks:
        raise ExtractionError('No readable blocks')
    starts = [i for i, b in enumerate(blocks) if START.search(b['text'])]
    if starts:
        # A marker must be a standalone apparatus block, never prose.
        blocks = blocks[starts[-1] + 1:]
    end_positions = [i for i, b in enumerate(blocks) if END.search(b['text'])]
    if end_positions:
        blocks = blocks[:end_positions[0]]
    # Modern pg-header/footer may have been omitted as semantic containers.
    footer_orders = [n.order for n in nodes if n.id.lower() in {'pg-footer', 'pgfooter'}]
    if footer_orders:
        blocks = [b for b in blocks if b['order'] < min(footer_orders)]
    if chapter_ids and chapter_texts:
        raise ExtractionError('Use chapter_ids or chapter_texts, not both')
    all_reading_blocks = list(blocks)
    explicit = bool(chapter_ids or chapter_texts)
    anchors = list(chapter_ids or [])
    if anchors:
        if len(anchors) != len(set(anchors)):
            raise ExtractionError('Duplicate chapter anchors')
        orders = [_anchor_order(parser, x) for x in anchors]
        if orders != sorted(orders):
            raise ExtractionError('Chapter anchors are not in source order')
        if start_id and _anchor_order(parser, start_id) > orders[0]:
            raise ExtractionError('Start bound excludes first chapter')
        start_id = start_id or anchors[0]
    else:
        orders = []
    if chapter_texts:
        if len(chapter_texts) != len(set(chapter_texts)):
            raise ExtractionError('Duplicate chapter text selectors')
        start_text = start_text or chapter_texts[0]
    lower = _anchor_order(parser, start_id) if start_id else None
    upper = _anchor_order(parser, end_id) if end_id else None
    if lower is not None and upper is not None and lower >= upper:
        raise ExtractionError('Reversed bounds')
    exclusions = set(exclude_ids)
    for x in exclusions:
        _anchor_order(parser, x)
    selected = []
    for b in blocks:
        reason = None
        if lower is not None and b['order'] < lower:
            reason = 'before-explicit-start'
        if upper is not None and b['order'] >= upper:
            reason = 'after-explicit-end'
        if any(n.id in exclusions for n in _ancestors(b['node'])):
            reason = 'explicit-exclusion'
        if reason:
            omitted.append({'reason': reason, 'source_id': b['source_id'], 'words': len(b['text'].split()), 'preview': b['text'][:100]})
        else:
            selected.append(b)
    blocks = selected
    for bound, inclusive in ((start_text, True), (end_text, False)):
        if bound is not None:
            positions = [i for i, b in enumerate(blocks) if b['text'] == bound]
            if not inclusive and end_text_occurrence is not None:
                if type(end_text_occurrence) is not int or not 1 <= end_text_occurrence <= len(positions):
                    raise ExtractionError('Invalid end text occurrence')
                pos = positions[end_text_occurrence - 1]
            else:
                if len(positions) != 1:
                    raise ExtractionError(f'Expected one text bound {bound!r}; found {len(positions)}')
                pos = positions[0]
            discarded = blocks[:pos] if inclusive else blocks[pos:]
            for b in discarded:
                omitted.append({'reason': 'explicit-text-bound', 'source_id': b['source_id'], 'words': len(b['text'].split()), 'preview': b['text'][:100]})
            blocks = blocks[pos:] if inclusive else blocks[:pos]
    if not blocks:
        raise ExtractionError('Bounds removed all reading text')
    warnings = []
    if parser.malformed:
        warnings.append('html-parser-recovery')
    if not explicit:
        if heading_level is not None and heading_level not in range(1, 7):
            raise ExtractionError('Invalid heading level')
        mixed_chapters = ([i for i, b in enumerate(blocks) if b['tag'] in {'h1','h2','h3','h4','h5','h6'}
                           and re.match(r'^chap(?:ter|\.)\s+', b['text'], re.I)]
                          if heading_level is None and not heading_pattern else [])
        if heading_level is None:
            headings2 = [b for b in blocks if b['tag'] == 'h2' and not APPARATUS.fullmatch(b['text'].strip(' .:'))]
            headings3 = [b for b in blocks if b['tag'] == 'h3' and CHAPTER.match(b['text'])]
            if len(headings3) >= 2 and sum(bool(CHAPTER.match(b['text'])) for b in headings2) < 2:
                heading_level = 3
            else:
                heading_level = 2
        heading_tag = 'h' + str(heading_level)
        candidates = [i for i, b in enumerate(blocks) if b['tag'] == heading_tag]
        if len(mixed_chapters) >= 2:
            boundary_indexes = mixed_chapters
            heading_level = 'mixed-chapter-headings'
        elif heading_pattern:
            pattern = re.compile(heading_pattern)
            boundary_indexes = [i for i in candidates if pattern.search(blocks[i]['text'])]
        else:
            numbered = [i for i in candidates if CHAPTER.match(blocks[i]['text'])]
            anchored = [i for i in candidates if re.search(r'(?:chap|chapter|CH)0*\d', blocks[i]['source_id'], re.I)]
            if len(numbered) >= 2:
                boundary_indexes = numbered
            elif len(anchored) >= 2:
                boundary_indexes = anchored
            else:
                boundary_indexes = [i for i in candidates if not APPARATUS.fullmatch(blocks[i]['text'].strip(' .:'))
                                    and not re.match(r'^by(?:\s|$)', blocks[i]['text'], re.I)
                                    and not re.fullmatch(r'(?:the end|finis)[.!]?', blocks[i]['text'], re.I)]
        for label in extra_heading_texts:
            matches = [i for i, b in enumerate(blocks) if b['tag'] in {'h1','h2','h3','h4','h5','h6'} and b['text'] == label]
            if not matches:
                raise ExtractionError('Missing extra heading: ' + label)
            boundary_indexes.extend(matches)
        boundary_indexes = sorted(set(boundary_indexes))
        if not boundary_indexes:
            raise ExtractionError('No chapter headings; specify chapter anchors')
        # Discard title/author material preceding the first section, reporting it.
        first = boundary_indexes[0]
        for b in blocks[:first]:
            omitted.append({'reason': 'before-first-heading', 'source_id': b['source_id'], 'words': len(b['text'].split()), 'preview': b['text'][:100]})
        blocks = blocks[first:]
        boundary_indexes = [i - first for i in boundary_indexes]
    else:
        boundary_indexes = []
        for text in chapter_texts or []:
            candidates = [i for i, b in enumerate(blocks) if b['text'] == text]
            if len(candidates) != 1:
                raise ExtractionError(f'Expected one chapter text {text!r}; found {len(candidates)}')
            boundary_indexes.append(candidates[0])
        if boundary_indexes != sorted(boundary_indexes):
            raise ExtractionError('Chapter text selectors are not in source order')
        for order in orders:
            candidates = [i for i, b in enumerate(blocks) if b['order'] >= order]
            if not candidates:
                raise ExtractionError('Chapter anchor has no readable content')
            boundary_indexes.append(candidates[0])
        if len(set(boundary_indexes)) != len(boundary_indexes):
            raise ExtractionError('Multiple chapter anchors resolve to same block')
        if boundary_indexes[0] != 0:
            raise ExtractionError('Content exists before first explicit chapter')
    sections = []
    for j, i in enumerate(boundary_indexes):
        last = boundary_indexes[j + 1] if j + 1 < len(boundary_indexes) else len(blocks)
        section = blocks[i:last]
        title_parts = []
        for b in section:
            if b['tag'] not in {'h1','h2','h3','h4','h5','h6'}:
                break
            title_parts.append(b['text'])
        title = ' — '.join(title_parts) or section[0]['text']
        sid = anchors[j] if anchors else section[0]['source_id']
        if APPARATUS.fullmatch(title.strip(' .:')):
            for b in section:
                omitted.append({'reason': 'apparatus-section', 'source_id': b['source_id'], 'words': len(b['text'].split()), 'preview': b['text'][:100]})
            continue
        sections.append((title, sid, section))
    if not sections:
        raise ExtractionError('No narrative sections')
    chapters, kept = [], []
    pending = []
    for title, sid, section in sections:
        bodywords = sum(len(b['text'].split()) for b in section[1:])
        if bodywords == 0 and not explicit:
            pending.extend(section)
            continue
        if pending:
            section = pending + section
            title = ' — '.join(b['text'] for b in pending) + ' — ' + title
            pending = []
        if bodywords < min_chapter_words:
            warnings.append('short-section:' + (sid or title[:40]))
        text = '\n\n'.join(b['text'] for b in section).strip() + '\n'
        chapters.append({'title': title, 'text': text, 'source_id': sid,
                         'word_count': len(text.split())})
        kept.extend(section)
    if pending:
        raise ExtractionError('Trailing heading without chapter body')
    if len(chapters) < 2:
        warnings.append('fewer-than-two-sections')
    if not chapters:
        raise ExtractionError('No chapter prose')
    prefatory_chapters, prefatory_kept = [], []
    for entry in prefatory_sections:
        if not isinstance(entry, dict) or set(entry) != {'title', 'text'} or not isinstance(entry['title'], str) or not entry['title'].strip():
            raise ExtractionError('Invalid prefatory section selector')
        matches = [b for b in all_reading_blocks if b['text'] == entry['text']]
        if len(matches) != 1:
            raise ExtractionError('Prefatory section text must match exactly one source block')
        block = matches[0]
        if block['order'] >= kept[0]['order'] or block in prefatory_kept:
            raise ExtractionError('Prefatory section overlaps or follows narrative')
        prefatory_kept.append(block)
        text = block['text'] + '\n'
        prefatory_chapters.append({'title': entry['title'].strip(), 'text': text, 'source_id': block['source_id'], 'word_count': len(text.split())})
        omitted = [x for x in omitted if not (x['preview'] == block['text'][:100] and x['words'] == len(block['text'].split()) and x['reason'] in {'before-explicit-start','before-first-heading','explicit-text-bound'})]
    if [b['order'] for b in prefatory_kept] != sorted(b['order'] for b in prefatory_kept):
        raise ExtractionError('Prefatory sections are not in source order')
    chapters = prefatory_chapters + chapters
    kept = prefatory_kept + kept
    if chapter_titles:
        if not isinstance(chapter_titles, dict) or any(not isinstance(v, str) or not v.strip() for v in chapter_titles.values()):
            raise ExtractionError('Invalid chapter title mapping')
        for sid, title in chapter_titles.items():
            matches = [c for c in chapters if c['source_id'] == sid]
            if len(matches) != 1:
                raise ExtractionError('Chapter title must match exactly one source ID')
            matches[0]['title'] = title.strip()
    texts = [c['text'] for c in chapters]
    if len({sha256(t.encode()).hexdigest() for t in texts}) != len(texts):
        raise ExtractionError('Duplicate chapter text')
    if any(START.search(t) or END.search(t) or 'www.gutenberg.org/license' in t for t in texts):
        raise ExtractionError('Gutenberg apparatus leaked into reading text')
    reconstructed = '\n\n'.join(b['text'] for b in kept).strip() + '\n'
    joined = '\n\n'.join(t.strip() for t in texts) + '\n'
    if joined != reconstructed:
        raise ExtractionError('Chapter reconstruction differs from selected blocks')
    if sum(x['words'] for x in omitted if x['reason'] == 'before-first-heading') > 1500:
        warnings.append('large-omitted-front-matter')
    if any(re.search(r'transcriber[’\x27]s?\s+notes?|Project Gutenberg Etext|books? for the young|\bprice\b.{0,60}\bnet\b', t, re.I) for t in texts):
        warnings.append('review-possible-apparatus')
    if any(re.match(r'^(?:preface|introduction|appendix|notes)(?:\b|$)', c['title'], re.I) for c in chapters):
        warnings.append('review-front-or-back-matter')
    diagnostics = {
        'chapter_count': len(chapters), 'word_count': sum(c['word_count'] for c in chapters),
        'kept_blocks': len(kept), 'omitted_blocks': len(omitted), 'omitted': omitted,
        'warnings': sorted(set(warnings)), 'heading_level': heading_level,
        'explicit_chapter_anchors': explicit, 'heading_pattern': heading_pattern, 'reconstruction_verified': True,
        'selected_text_sha256': sha256(reconstructed.encode()).hexdigest(),
        'html_sha256': sha256(original_bytes).hexdigest(),
        'parser_recoveries': parser.malformed,
        'completeness_note': 'Reconstruction checks selected source blocks only; source edition and chapter inventory require review.'
    }
    return {'chapters': chapters, 'diagnostics': diagnostics}
