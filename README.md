# TypeBook Resources

Standalone official resource catalog extracted from TypeBook.fun on November 2,
2026. This independent public repository contains resources, catalogs and validation tools;
the application source remains in its existing repository.

## Contents

| Resource | Included |
| --- | --- |
| Demo anthology | 3 original articles |
| Additional starter articles | 3 original articles retained in the official catalog |
| Books | 100 books, 123 stored chapters and 100 covers |
| Dictionaries | 28 dictionaries, 81,119 entries |
| Learning prompts | 3 preserved built-ins + 15 distinct learning, typing and image tasks; titles in English, Chinese and Japanese |
| Live2D models | 8 models, 158 files |
| Browser support assets | Existing speech model, WASM/runtime files, Live2D core and other public assets |

Original books:

- A Christmas Carol, Charles Dickens: 5 stored chapters.
- A Study in Scarlet, Arthur Conan Doyle: 14 stored chapters.
- The Wind in the Willows, Kenneth Grahame: 7 stored chapters.

The November 2026 reader addition contains 97 short English children’s books
from Hugging Face’s GlotStoryBook dataset, individually verified as CC BY 3.0
or CC BY 4.0. The second curated batch adds 81 books to the original 19-book
catalog. Each short reader has one complete-story chapter (21–687 words), source
attribution and an original typographic cover. See [the reading list and
reproducible importer](docs/huggingface-readers.md).

For the original three books, chapter boundaries and content are preserved as currently stored. This export
does not assert that every edition's original chapter structure is represented.
Dictionary JSON, chapter text, images and model binaries retain their original
bytes. Git attributes disable newline conversion for payload files.

## Multilingual book titles

All 100 books include `title_i18n` with `en`, `zh-CN` and `ja` display titles.
The existing English `title`, chapter text and original credits are unchanged.
See [the field contract and reproducible editing workflow](docs/book-titles.md).
Application integration is separate; this resource update does not deploy the site.

## Learning and typing prompts

The 18-prompt catalog preserves the original 3 built-ins and adds 15 focused
workflows: 7 English learning tasks, 3 typing tasks and 5 image generation tasks.
These include role-play, active vocabulary recall, grammar repair, precise
punctuation/number copying, typed-error review, word cards, spelling tiles and
wordless story sequences. Similar variants were deliberately consolidated.
All prompts include additive `title_i18n` labels for `en`, `zh-CN` and `ja`,
plus task, output and placeholder metadata. Existing English `name` values and
the three original prompt bodies are unchanged. See [task selection, field
contracts and local rendering](docs/prompts.md). Image entries are templates,
not generated images; a compatible consumer route is required. Application
integration and deployment remain separate.

## Layout

```text
manifest.json                Versioned catalog, relative paths, sizes and SHA-256
provenance.json              Source commit, export scope and exclusions
catalogs/                    Book, dictionary, article, prompt and model metadata
profiles/default.json        Suggested smaller frontend bundle
books/                       Chapter text and covers
collections/demo-anthology/  Original demo articles
articles/starter/            Existing additional starter articles
dictionaries/                Complete official dictionary JSON
prompts/                     Prompt source JSON and localized display metadata
live2d/models/               All eight model directories and their dependencies
paradee/, onnx-runtime/      Existing browser speech assets
tools/verify.py              Offline integrity and dependency checks
tools/import_hf_readers.py   Pinned, license-checked English reader importer
tools/hf_readers.json        Curated reading list and upstream checksums
tools/book_titles.json       English, Chinese and Japanese book display titles
tools/rebuild_prompts.py     Offline prompt validation, rendering and catalog rebuild
tests/                      Offline importer and prompt regression tests
docs/                       Hosting, frontend integration and rights notes
```

All catalog paths are relative to this repository root. Resolve them against
the manifest directory, rather than against the website's origin.
`manifest.json` covers the payloads and supporting files; it excludes itself.
It contains no API keys, credentials, private user content or user progress.

## Verify locally

Python 3 is sufficient; no npm installation or backend is needed.

```sh
python3 tools/rebuild_prompts.py --check
python3 tools/verify.py
python3 -m unittest discover -s tests -v
```

The validator checks every recorded file's size and SHA-256, dictionary entry
counts, chapter references, prompt files, model dependencies and the default
profile. This validates a resource repository, not a running TypeBook application.

## Recommended distribution

The full resource set is approximately 259 MiB. Live2D files account for about
211 MiB. The suggested default profile is about 61 MiB including the existing
browser runtimes: all books, dictionaries, prompts and demo/starter texts, plus
the Yuki model. The other seven models can be loaded on demand.

TypeBook's selected default source is this public repository. The application
pins a specific commit and verifies downloaded catalogs and text payloads.
The default profile also describes a possible smaller bundled distribution.
Load individual dictionaries, chapters and models only when opened;
shipping static files does not require downloading all of them at startup.

See [the implementation assessment](docs/frontend-resource-strategy.md).
Application integration is maintained in the separate application repository.
Existing Cloudflare R2 objects and D1 rows are retained.

## Repository

Public repository: https://github.com/jianchengwang/typebook-resources

For a new checkout:

```sh
git clone https://github.com/jianchengwang/typebook-resources.git
```

Use the `manifest.json` at a fixed commit or release when
configuring an app. A `main` URL is convenient for browsing, but its contents
can change. See [the hosting contract](docs/resource-hosting.md).

## Rights

Existing notices and attribution are preserved. A resource being configured as
"official" in TypeBook does not assign it a new redistribution license.
Third-party resources without recorded license metadata remain marked
`not-recorded-in-source`; this repository assigns no blanket MIT or other
license to those assets. Review [the resource rights notes](docs/RIGHTS.md)
before public distribution.
