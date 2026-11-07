# Lightweight manifest v2 and dictionary titles

The root `manifest.json` is a small discovery index with `schema_version: 2`.
It no longer embeds every chapter, source file and asset record. This is an
intentional breaking change; the website importer is not changed here.

## Structure and loading

- `catalogs`, `profiles` and `compatibility` map names to `{path, bytes, sha256}`.
- `file_inventory` points to `catalogs/files.json`, with its byte length and hash.
  That file has `schema_version: 1` and the complete `files` array, preserving
  every `path`, `bytes`, `sha256`, `content_type` and `category`.
- `file_sources` points to `catalogs/file-sources.json`, with its length and hash.
  This optional audit index deduplicates source provenance: `files[path]` is an
  index into its `sources` array. `sources[files[path]]` recovers `file.source`.
- `counts`, `revision`, the repository ID and other identifying metadata remain.
- `total_bytes` counts every inventoried repository file plus the inventory
  itself, excluding only `manifest.json`. The inventory excludes itself and the
  root manifest to avoid circular checksums; its own hash is in the root.

Recommended frontend flow:

1. Accept manifest schema version 2. Resolve safe relative paths against the
   manifest URL, ideally pinned to one immutable Git commit.
2. Load only the catalog for the active tab from `manifest.catalogs[name]`.
   Verify its exact byte length and SHA-256 using that reference directly.
3. Show the catalog's resource metadata. When importing selected text resources,
   fetch their `body`/`cover` references and verify their existing size and hash.
4. Fetch and verify `file_inventory` only when a full file map is needed, such as
   resolving all Live2D textures, model dependencies, runtime files or a profile.
   Read `inventory.files` instead of the removed `manifest.files`.
5. Fetch `file_sources` only for source auditing. Ordinary browsing/import does
   not need it. Preserve per-book license files and attribution requirements.

Never disable hash/path verification simply because inventory loading is lazy.
Reject unsupported versions, unsafe paths and duplicate file paths. Check each
index against its reference before trusting it. `tools/manifest_io.py` is the
full offline loader used by rebuilders and `tools/verify.py`; it verifies the
index chain and expands records for tooling. It still accepts v1 as migration
input, but all new output is v2.

## What this does not change

All original resource files, IDs and metadata remain. No chapter files are
combined or removed. `catalogs/books.json` remains the existing full book catalog
(about 2.8 MB raw), including all chapter metadata. A truly minimal book-list
view would additionally need a book-summary catalog and per-book chapter indexes;
that separate restructuring is not implemented here. Thus the tiny root manifest
alone does not promise an equivalent reduction in complete book-tab loading time.

HTTP gzip/Brotli and CDN caching remain separate hosting concerns. The compact
file inventory and source audit index remain available on demand rather than
being deleted. Existing v1-only importers will reject v2 until updated; using a
previous Git commit remains an option during migration.

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
