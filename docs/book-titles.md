# Multilingual book titles

All 100 entries in `catalogs/books.json` include an additive `title_i18n` object:

```json
{
  "id": "book:1",
  "title": "A Christmas Carol",
  "title_i18n": {
    "en": "A Christmas Carol",
    "zh-CN": "圣诞颂歌",
    "ja": "クリスマス・キャロル"
  }
}
```

- `title` is still the original English title, unchanged. Existing consumers can
  continue reading it. `title_i18n.en` is exactly the same string.
- `zh-CN` is Simplified Chinese; `ja` is Japanese. These are display titles to
  help readers choose a book, not translations of the chapters. They are
  TypeBook editorial labels, not a claim of publisher approval or of an official
  translated edition. Established titles are used for the three classic books.
- Names are transliterated consistently. Ambiguous titles were checked against
  story text: for example, *Keeper and His Special Nursery* concerns animal
  orphans, *Chicken and Millipede* uses a millipede rather than a centipede, and
  *Bunty and Bubbly* features a soap king.
- Book IDs, English titles, author names, descriptions, chapters, covers, source
  files, copyright notices and license metadata are unchanged. Only the book
  metadata revision increments for a changed title map. Chapter revisions stay
  unchanged because their text has not changed.

## Consumer contract

Use `book.title_i18n?.[locale] || book.title`. The supported locale keys match
TypeBook's existing interface locales: `en`, `zh-CN`, and `ja`. Fall back to
`title` for an unknown locale or an older catalog without `title_i18n`. A
consumer may show the English `title` underneath a translated title and search
all three values to make selection easier.

This change is confined to the resource repository. Application import and
interface integration are separate work; adding these fields does not by itself
change the live website. Consumers pinning a resource commit must update that
pin and manifest checksums when adopting this catalog.

## Editing and reproducing

`tools/book_titles.json` is the single editorial source, keyed by stable book
ID. Edit its Chinese/Japanese title values, then regenerate:

```sh
python3 tools/import_hf_readers.py --write --offline
python3 tools/import_hf_readers.py --check --offline
python3 tools/verify.py
python3 -m unittest discover -s tests -v
```

Omit `--offline` on a new checkout so the importer can retrieve its pinned,
checksum-verified original inputs. This is the existing book importer: the title
map is applied after combining the three classic books with the 97 readers, so
future imports cannot silently erase localized titles. A newly selected book
must also receive an entry in the title map; missing/unknown IDs, missing or
unsupported locales, blank/control-character titles, and changed English titles
are rejected before writing. Re-running with unchanged inputs is a no-op.
