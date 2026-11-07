#!/usr/bin/env python3
"""Rebuild pinned English-original readers offline; sources must already be verified.

No network access. --write applies an atomic, recoverable plan; --check verifies
reproducibility. Copyright clearance is editorial, not inferred from a checksum.
"""
import argparse
import copy
import html
import json
import pathlib
import re
import sys
import textwrap
from html.parser import HTMLParser
from import_hf_readers import (ROOT, apply_plan, body_ref, json_bytes, recover_transaction,
                              require, resource_files, safe_path, sha256, transaction_directory)
from gutenberg_text import extract_book

IMPORT_ID = 'gutenberg-english-youth-v1'
SUPPORT = {'tools/import_gutenberg_readers.py', 'tools/gutenberg_text.py',
           'tools/gutenberg_readers.json', 'tests/test_gutenberg_readers.py',
           'tests/test_gutenberg_text.py', 'docs/english-original-readers.md'}

class Plain(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []
    def handle_data(self, value): self.parts.append(value)
    def handle_starttag(self, tag, attrs):
        if tag in ('p','div','section','br','h1','h2','h3','li','pre'): self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('p','div','section','h1','h2','h3','li','pre'): self.parts.append('\n')

def plaintext(value):
    p=Plain(); p.feed(value.replace('\r\n','\n').replace('\r','\n'))
    return re.sub(r'\n\s*\n\s*\n+', '\n\n', ''.join(p.parts)).strip()

def source_bytes(root, cache, book, suffix):
    if cache is not None:
        path=cache / f'{book["gutenberg_id"]}{suffix}'
    else:
        path=safe_path(root, f'books/{book["slug"]}/' + {'.html':'original.html','.page.html':'catalog.html'}[suffix])
    data=path.read_bytes()
    expected=book['text_sha256' if suffix=='.html' else 'page_sha256']
    require(sha256(data)==expected, 'Pinned source mismatch: '+str(path))
    return data

def validate_config(config):
    require(config.get('schema_version')==1 and config.get('import_id')==IMPORT_ID, 'Invalid reader configuration')
    books=config['books']; require(bool(books), 'No readers selected')
    require(len({b['gutenberg_id'] for b in books})==len(books), 'Duplicate source edition')
    require(len({b['slug'] for b in books})==len(books), 'Duplicate book folder')
    for b in books:
        require(type(b['gutenberg_id']) is int and 0<b['gutenberg_id']<100000, 'Invalid Gutenberg ID')
        require(re.fullmatch(r'pg-[a-z0-9]+(?:-[a-z0-9]+)*',b['slug']), 'Unsafe book slug')
        require(b['original_language']=='en' and b['rights']['source_status']=='Public domain in the USA.', 'Unverified original language/rights')
        require(type(b['rights']['author_death_year']) is int and 1000<=b['rights']['author_death_year']<=1955, 'Author life dates outside selection policy')
        require(b['rights']['reviewed'] is True and b['completeness']['reviewed'] is True, 'Unreviewed book')
        require(set(b['title_i18n'])=={'en','zh-CN','ja'}, 'Missing title translation')
        require(b['title']==b['title_i18n']['en'], 'English title mismatch')
        require(all(isinstance(x,str) and x.strip()==x and x for x in b['title_i18n'].values()), 'Empty title')
        for key in ('page_sha256','text_sha256'):
            require(re.fullmatch('[0-9a-f]{64}',b[key]), 'Missing source pin')
        require(b['text_url'].startswith('https://www.gutenberg.org/'), 'Unexpected text source')

def cover(title,author,words):
    lines=textwrap.wrap(title, width=27)
    size=27 if len(lines)<6 else 22
    lines=lines[:9]
    rendered=''.join(f'<text x="42" y="{165+i*38}" font-size="{size}" font-weight="700">{html.escape(t)}</text>' for i,t in enumerate(lines))
    names=textwrap.wrap(author,40)
    names=''.join(f'<text x="42" y="{530+i*22}" font-size="15">{html.escape(t)}</text>' for i,t in enumerate(names[:2]))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="640" viewBox="0 0 480 640">\n'
            f'<rect width="480" height="640" fill="#f3efe5"/><rect x="0" y="0" width="12" height="640" fill="#355f67"/>'
            f'<g font-family="serif" fill="#223c42"><text x="42" y="65" font-size="15">ENGLISH ORIGINAL READERS</text>{rendered}{names}'
            f'<text x="42" y="605" font-size="14">{words:,} words · Original English text</text></g></svg>\n').encode()

def build_book(root,cache,b):
    raw=source_bytes(root,cache,b,'.html'); page=source_bytes(root,cache,b,'.page.html')
    require('Public domain in the USA.' in page.decode('utf-8'), 'Source page no longer declares US public domain')
    result=extract_book(raw.decode('utf-8-sig'), **b.get('extraction',{}))
    segments=result['chapters']
    require(len(segments)==b['completeness']['section_count'], 'Section count mismatch: '+b['title'])
    require(result['diagnostics']['selected_text_sha256']==b['completeness']['selected_text_sha256'], 'Extracted text differs from reviewed source: '+b['title'])
    require([c['title'] for c in segments]==b['completeness']['section_titles'], 'Section inventory differs: '+b['title'])
    require(len(segments)>=2, 'Single-story item is not a full reader: '+b['title'])
    words=sum(len(c['text'].split()) for c in segments)
    require(words==b['completeness']['word_count'], 'Word count mismatch: '+b['title'])
    require(words>=5000, 'Unexpectedly short full reader: '+b['title'])
    folder='books/'+b['slug']; ident=900000+b['gutenberg_id']; outputs={}
    outputs[folder+'/original.html']=raw; outputs[folder+'/catalog.html']=page
    footer=re.search(r'<(?:section|div|footer)[^>]+id=["\']pg-footer["\'][^>]*>(.*)',raw.decode('utf-8-sig'),re.S|re.I)
    # Keep an exact original HTML too; license transcription is a convenience copy.
    require(footer is not None, 'Missing full source license footer: '+b['title'])
    license_text=plaintext(footer.group(1))
    require('FULL PROJECT GUTENBERG LICENSE' in license_text.upper(), 'Missing Gutenberg license')
    require(len(license_text)>10000, 'Truncated license footer')
    notice=(f'# {b["title"]}\n\nAuthor: {b["author"]}.\n\n'
            f'Source: https://www.gutenberg.org/ebooks/{b["gutenberg_id"]}\n\n'
            'The source edition is marked **Public domain in the USA**. This is not a worldwide copyright clearance. '
            'Check the law where you distribute or use it. Original English text only; no publisher cover or source illustrations are redistributed as practice assets. '
            'Our cover is a new typographic design. Display titles in Chinese/Japanese are editorial labels, not translations of the book.\n\n'
            'Practice text removes source navigation, illustrations and publishing apparatus; it does not abridge or simplify the story. '
            'The original downloaded HTML is retained as original.html, with its full notices and license. Extraction decisions are recorded in source.json.\n\n'
            '## Full source license and notices (plain-text transcription)\n\n'+license_text+'\n')
    outputs[folder+'/LICENSE.md']=notice.encode()
    chapters=[]
    for n,c in enumerate(segments,1):
        data=(c['text'].strip()+'\n').encode(); path=f'{folder}/chapters/{n:03d}.txt';outputs[path]=data
        cid=900000000+b['gutenberg_id']*1000+n
        chapters.append({'book_id':ident,'title':c['title'],'chapter_number':n,'word_count':len(c['text'].split()),
                         'revision':1,'id':f'chapter:{cid}','legacy_id':cid,'body':body_ref(path,data),
                         'source_url':b['text_url']+('#'+c['source_id'] if c.get('source_id') else ''),
                         'attribution':b['author']+'; source edition: Project Gutenberg. Plain-text extraction; no narrative abridgement.',
                         'adaptation_note':'Navigation, illustrations and publishing apparatus omitted from practice text; complete source HTML retained.',
                         'license_label':'Public domain in the USA; Project Gutenberg source terms',
                         'license_url':f'https://www.gutenberg.org/ebooks/{b["gutenberg_id"]}',
                         'source_section_id':c.get('source_id')})
    artwork=cover(b['title'],b['author'],words);outputs[folder+'/cover.svg']=artwork
    source={'schema_version':1,'import_id':IMPORT_ID,**b,'extraction_diagnostics':result.get('diagnostics',{}),
            'adaptation':'Plain text extraction only. No abridgement, simplification or generated replacement narrative.',
            'cover':'New typographic cover; no source artwork used.',
            'chapter_bodies':[c['body'] for c in chapters]}
    outputs[folder+'/source.json']=json_bytes(source)
    practice=b['practice']
    description=(f'{b["author"]}. Complete English-original {b["genre"]} reader. '
                 f'{len(chapters)} reading sections, {words:,} words. '
                 'Historic vocabulary; not a graded or simplified reader. '
                 'Source: Project Gutenberg; public domain in the USA, check local rights. '
                 + ('Content notes: '+'; '.join(practice.get('content_notes',[]))+'.' if practice.get('content_notes') else ''))
    book={'id':f'book:{ident}','legacy_id':ident,'title':b['title'],'title_i18n':b['title_i18n'],
          'author':b['author'],'description':description,'tags':json.dumps(['english-original','children-youth',b['genre']]),
          'word_count':words,'chapter_count':len(chapters),'revision':1,'license_status':'verified-public-domain-us',
          'license':{'id':'Public-domain-US','label':'Public domain in the USA; check local law','url':f'https://www.gutenberg.org/ebooks/{b["gutenberg_id"]}'},
          'cover':body_ref(folder+'/cover.svg',artwork),'chapters':chapters,'practice':practice,
          'source':{'import_id':IMPORT_ID,'kind':'project-gutenberg','gutenberg_id':b['gutenberg_id'],'path':folder+'/source.json',
                    'url':f'https://www.gutenberg.org/ebooks/{b["gutenberg_id"]}'}}
    return book,outputs

def make_plan(root,config,cache=None):
    validate_config(config)
    manifest=json.loads((root/'manifest.json').read_text()); recorded={x['path']:x for x in manifest['files']}
    public=json.loads((root/'catalogs/books.json').read_text())
    owned=[b for b in public if b.get('source',{}).get('import_id')==IMPORT_ID]
    others=[b for b in public if b not in owned]
    archive=json.loads((root/'catalogs/standalone-readers.json').read_text())
    outputs={};new=[]
    for b in config['books']:
        book,files=build_book(root,cache,b);new.append(book);outputs.update(files)
    require({b['id'] for b in owned}<={b['id'] for b in new}, 'Removing imported readers is not supported')
    require(not {b['id'] for b in new}&{b['id'] for b in others+archive}, 'Book ID collision')
    chapter_ids=[c['id'] for b in new+others+archive for c in b['chapters']]
    require(len(chapter_ids)==len(set(chapter_ids)), 'Chapter ID collision')
    # Preserve all existing ordinary books and keep the anthology last, as its rebuild contract requires.
    anthologies=[b for b in others if b.get('source',{}).get('kind')=='curated-story-anthology' or b['id']=='book:810000']
    books=[b for b in others if b not in anthologies]+new+anthologies
    outputs['catalogs/books.json']=json_bytes(books)
    titles=json.loads((root/'tools/book_titles.json').read_text())
    for b in new:
        require(b['id'] not in titles['books'] or titles['books'][b['id']]==b['title_i18n'], 'Locally edited title: '+b['id'])
        titles['books'][b['id']]=b['title_i18n']
    outputs['tools/book_titles.json']=json_bytes(titles)
    summary=json.loads((root/'catalogs/summary.json').read_text())
    summary.update(books=len(books),chapters=sum(b['chapter_count'] for b in books),
                   stored_chapter_payloads=len({c['body']['path'] for b in books+archive for c in b['chapters']}))
    outputs['catalogs/summary.json']=json_bytes(summary)
    profile=json.loads((root/'profiles/default.json').read_text());profile['books']=[b['id'] for b in books]
    # Source HTML remains available on demand but is not part of the default practice bundle.
    profile['files']=sorted(set(profile['files'])|{p for p in outputs if p.startswith('books/') and not p.endswith('.html')})
    profile['payload_bytes']=sum(len(outputs[p]) if p in outputs else safe_path(root,p).stat().st_size for p in profile['files'])
    outputs['profiles/default.json']=json_bytes(profile)
    actual={p.relative_to(root).as_posix() for p in resource_files(root)}
    require(not set(recorded)-actual-set(outputs), 'Missing previously recorded files')
    require(not actual-set(recorded)-set(outputs)-SUPPORT, 'Unexpected untracked files: '+str(actual-set(recorded)-set(outputs)-SUPPORT))
    owned_folders={'books/'+b['slug']+'/' for b in config['books']}
    for p,data in outputs.items():
        current=safe_path(root,p)
        if current.exists() and current.read_bytes()!=data and p.startswith('books/'):
            require(p in recorded and sha256(current.read_bytes())==recorded[p]['sha256'], 'Locally edited payload: '+p)
            require(any(p.startswith(f) for f in owned_folders), 'Unowned payload replacement')
    files=[]
    for p in sorted(actual|set(outputs)):
        current=safe_path(root,p);require(not current.is_symlink(), 'Symlinked resource')
        data=outputs[p] if p in outputs else current.read_bytes()
        item=dict(recorded.get(p,{}));item.update(path=p,bytes=len(data),sha256=sha256(data))
        item.setdefault('content_type',{'.txt':'text/plain','.html':'text/html','.json':'application/json','.svg':'image/svg+xml','.md':'text/markdown','.py':'text/x-python'}.get(current.suffix,'application/octet-stream'))
        item.setdefault('category','book' if p.startswith('books/') else 'documentation' if p.startswith('docs/') else 'tooling')
        if any(p.startswith(f) for f in owned_folders):
            folder=next(f for f in owned_folders if p.startswith(f))
            item['source']={'kind':'curated-gutenberg-import','import_id':IMPORT_ID,'provenance':folder+'source.json'}
        files.append(item)
    changed=any(not (root/p).exists() or (root/p).read_bytes()!=data for p,data in outputs.items())
    manifest.update(counts=summary,files=files,total_bytes=sum(f['bytes'] for f in files))
    if changed: manifest['revision']=config['revision']
    outputs['manifest.json']=json_bytes(manifest)
    return outputs

def main():
    p=argparse.ArgumentParser(description=__doc__);m=p.add_mutually_exclusive_group()
    m.add_argument('--write',action='store_true');m.add_argument('--check',action='store_true')
    p.add_argument('--source-cache',type=pathlib.Path)
    p.add_argument('--recover',action='store_true',help='Recover an interrupted atomic write')
    args=p.parse_args()
    if args.recover:
        recover_transaction(ROOT);print('Recovered interrupted reader import');return
    require(not transaction_directory(ROOT).exists(), 'Interrupted import exists; run --recover first')
    config=json.loads((ROOT/'tools/gutenberg_readers.json').read_text())
    plan=make_plan(ROOT,config,args.source_cache)
    changed=[f for f,b in plan.items() if not (ROOT/f).is_file() or (ROOT/f).read_bytes()!=b]
    if args.check: require(not changed, 'Rebuild differs: '+str(changed))
    if args.write: apply_plan(ROOT,plan,changed)
    print(json.dumps({'status':'ok','mode':'write' if args.write else 'check' if args.check else 'dry-run',
                      'new_collection_books':len(config['books']),'changed_files':len(changed)},indent=2))
if __name__=='__main__':
    try: main()
    except (ValueError,KeyError,OSError) as e:
        print('Reader import failed: '+str(e),file=sys.stderr);raise SystemExit(1)
