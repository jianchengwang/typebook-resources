# Compact manifest and dictionary titles

The root URL and `schema_version: 1` are unchanged. Every file still has its
original `path`, `bytes`, `sha256`, `content_type` and `category`. All payloads,
IDs, catalogs, compatibility links, counts and SHA-256 verification remain.
JSON is formatted with one compact file record per line instead of deeply
indented records.

Only the optional per-file `source` audit metadata moves out of the hot path:

- `manifest.file_sources.path` points to `catalogs/file-sources.json`.
- That file is itself covered by the root manifest's byte length and SHA-256.
- Its `sources` array stores each unique source object once.
- Its `files` object maps each relative file path to a zero-based source index.
- Join `sources[files[path]]` to recover the original `file.source` exactly.
- Verify the sidecar's checksum before reading it. The sidecar cannot include its
  own hash; that hash belongs in the root manifest.

Existing importers using file paths, hashes, sizes and MIME types do not need
changes. Tools that read `manifest.files[*].source` must use the optional sidecar
(or `tools/manifest_io.py:load_manifest`). Do not interpret a missing inline
source as missing attribution or permission. Per-book source files and license
notices remain unchanged. `tools/verify.py` validates the sidecar too.

This reduces the initial manifest response, not the complete repository download.
It does not change catalog loading or split `catalogs/books.json`. HTTP gzip or
Brotli is a separate hosting concern; the reduction in raw JSON bytes must not
be interpreted as the same reduction in compressed network traffic.

## Dictionary display titles

All 28 dictionary records now include `title_i18n` with `en`, `zh-CN` and `ja`,
matching book and prompt title metadata. Existing `name`, IDs, payload bytes,
word counts and licenses are preserved. Prefer `title_i18n[locale]`, then
`title_i18n.en`, then `name`; the website importer is not changed here.

`tools/dictionary_titles.json` is the editorial source. Unclear source labels
such as WSCD remain labels rather than guessed expansions. NEW-series labels
are retained without asserting a textbook edition or publication year. The
legacy `NEC-NEW-4` spelling remains unchanged in `name` and file paths.
Title changes increment the dictionary metadata revision once. No translation
or replacement of dictionary entries is performed.

## Rebuild and verify

```sh
python3 tools/rebuild_metadata.py --write
python3 tools/rebuild_metadata.py --check
python3 tools/verify.py
python3 -m unittest discover -s tests -v
python3 tools/rebuild_prompts.py --check
python3 tools/import_gutenberg_readers.py --check
```

The existing book and prompt rebuilders use the same manifest serializer, so
later imports do not restore the bulky format or discard source audit records.
Metadata writes use the existing transactional writer: payloads and sidecar are
installed before the manifest, with rollback on failure. Publish and consume a
fixed Git commit for an atomic snapshot.

After an interrupted metadata write, run `python3 tools/rebuild_metadata.py --recover`
before rebuilding. Recovery restores the previous snapshot before its source-index
checksum is read.
