# Children's Short Stories / 儿童短故事合集 / 子どもの短いお話集

The public book catalog now offers **three independent long-form readers and one
children's short-story anthology**. A complete short story is one chapter; it is
not presented as a separate one-chapter collection. Original continuous chapters
in A Christmas Carol (5), A Study in Scarlet (14), and The Wind in the Willows (7)
remain separate and unchanged. No text from The Little Prince or Sophie's World
has been added.

The anthology contains **100 stories / 100 chapters, 20,229 words** in total
(21–687 words per story). Together with the three long-form readers, the public
catalog has 126 chapters. The final three additions are *The Big Juicy Mango*,
*My new friends*, and *The day we saw the rainbow*, checked against the same
pinned upstream and dataset.

## Structure and rights

- Public book: `book:810000`, `Children's Short Stories`, with English, Simplified
  Chinese and Japanese title/description metadata.
- One complete English story per chapter, ordered by word count then original
  stable numeric ID. This is an arrangement by length, not a certified CEFR scale.
- Every chapter retains the original title, body reference, word count, source URL,
  author/contributor attribution, CC BY 3.0 or 4.0 link, and normalization notice.
  Chapter display titles also have all three locales; story text stays English.
- `books/childrens-short-stories/LICENSE.md` contains all individual rights notices.
  There is no blanket license assigned to the collection's third-party texts.
- Body files under `books/asp-*/chapters/001.txt` are referenced directly. There is
  **zero duplicated story text** and no rewritten text or embedded credit text in
  the typing exercise. Only the new cover, combined credits and metadata are added.

## Preservation and old-to-new mapping

`catalogs/books.json` contains only the four public books. The former standalone
short-reader records, including their IDs and covers, are in
`catalogs/standalone-readers.json`. `manifest.compatibility.archived_books` points
to that file; it is not a second public browsing catalog. All source files,
original Markdown, licenses and covers remain present and integrity-checked.

`catalogs/reader-migrations.json` records every original `source_book_id` and
`source_chapter_id`, the anthology book/chapter ID and chapter number, and the
unchanged body path/hash/size. The new chapter ID is the old numeric chapter ID
plus 100000. Its identity does not depend on position, so a later editorial reorder
does not change IDs. The default profile lists only the four public book IDs,
while retaining the old files and archive for recovery/compatibility.

This is **not an automatic progress migration or deletion**. Existing local
copies and reading progress are untouched. Pinned older resource commits still
contain their original public catalogs. Consumers that update their pin and need
old official book/chapter lookups must explicitly read the compatibility archive
or consult the mapping. The current app does not do that automatically.

## Using it in TypeBook

1. Open the reading resource importer and refresh the official resource source.
2. Select **儿童短故事合集 / Children's Short Stories** once. The three long-form
   readers remain independent choices; standalone short stories are no longer
   offered in this updated source's default picker.
3. Importing the same anthology again is skipped by the current importer. Existing
   local single-story books remain as they were; do not delete them to adopt this
   anthology, especially if they contain user progress or edits.
4. For a reproducible source, use this repository's manifest URL at the published
   commit. The `main` source follows updates after refresh/CDN propagation.

This change only updates **typebook-resources**. The separate app's baked-in
`officialResourceIndex.json` still pins its previous commit until the user updates
it. Publishing resources does not deploy or modify the main website.

### Audited consumer limitations

Read-only audit of TypeBook's `frontend/src/utils/resourceImport.ts`,
`officialResourceStore.ts` and `localRepository.ts` confirmed that chapter bodies
may use any safe manifest-listed path, including the unchanged original folders.
There is no anthology chapter-count cap (the 32 MiB limit applies per file).

The current local importer keeps only chapter title and content, dropping chapter
translation, original IDs and license metadata. Therefore the anthology's English
**book description also contains all per-story credit, source and license notices**,
which that importer preserves, as well as a link to the complete combined credits.
The long description is intentional for compatibility; future app work can render
credits separately. Chapter `title_i18n` is additive and requires consumer support.
The official collection loader displays the flat `attribution`, `license_label`
and `license_url` fields, which are retained; it replaces chapter author with book
author, so the exact author is also retained within the attribution text.

## Rebuild and validate

The anthology is automatically regenerated by the existing pinned source importer:

```sh
python3 tools/import_hf_readers.py --write --offline
python3 tools/import_hf_readers.py --check --offline
python3 tools/rebuild_prompts.py --check
python3 tools/verify.py
python3 -m unittest discover -s tests -v
```

For a fresh checkout omit `--offline` once to retrieve checksum-verified pinned
inputs. `tools/story_anthology.json` defines IDs, archive and mapping paths;
`tools/book_titles.json` includes public and archived titles. Re-running does not
append duplicate chapters, relist archived books, duplicate text or bump revisions
without changed metadata. The writer backs up changed files, commits the manifest
last and supports `--recover` after an interruption. Unknown files, changed source
hashes, ID collisions and missing attribution fail before writing.
