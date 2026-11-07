# TypeBook Resources

Standalone official resource catalog extracted from TypeBook.fun on November 2,
2026. This independent public repository contains resources, catalogs and validation tools;
the application source remains in its existing repository.

## Contents

| Resource | Included |
| --- | --- |
| Demo anthology | 3 original articles |
| Additional starter articles | 3 original articles retained in the official catalog |
| Books | 100 public entries: 96 new English-original readers + 3 retained books + one 100-story anthology; 2,387 reading sections; 100 standalone records retained for compatibility |
| Dictionaries | 28 dictionaries, 81,119 entries |
| Learning prompts | 3 preserved built-ins + 13 distinct English learning, image and children's story tasks; titles and prompt bodies in English, Chinese and Japanese |
| Live2D models | 8 models, 158 files |
| Browser support assets | Existing speech model, WASM/runtime files, Live2D core and other public assets |

Original books:

- A Christmas Carol, Charles Dickens: 5 stored chapters.
- A Study in Scarlet, Arthur Conan Doyle: 14 stored chapters.
- The Wind in the Willows, Kenneth Grahame: 7 stored chapters.

The November 2026 reader addition contains 100 short English children’s stories
from Hugging Face’s GlotStoryBook dataset, individually verified as CC BY 3.0
or CC BY 4.0. They are now presented as **Children's Short Stories / 儿童短故事合集**, one complete
story per chapter, rather than 100 separate one-chapter books. The three original
long-form readers remain independent. Old standalone IDs, source files and covers
are preserved in a compatibility catalog, not repeated in the default book picker.
See [the anthology structure and import notes](docs/childrens-short-stories.md) and
[the reading list and reproducible importer](docs/huggingface-readers.md).

For the original three books, chapter boundaries and content are preserved as currently stored. This export
does not assert that every edition's original chapter structure is represented.
Dictionary JSON, chapter text, images and model binaries retain their original
bytes. Git attributes disable newline conversion for payload files.

## English-original children and youth readers

The new collection adds **96 complete narrative works** from pinned Project Gutenberg
editions: fantasy, growing-up stories, adventures, animals and genuine story collections.
Examples include *Alice’s Adventures in Wonderland*, *The Wonderful Wizard of Oz*,
*The Secret Garden*, *A Little Princess*, *Anne of Green Gables*, *Little Women*,
*The Railway Children*, *Black Beauty* and *Treasure Island*.
Together the new books provide **2,261 reading sections and 6,304,068 words**.
Sections follow chapters, stories, letters and literary framing as appropriate;
they are not 2,261 independently numbered original chapters. *Little Women* has
both parts and 47 chapters. The prior books and short-story anthology remain intact.

All new entries have English, Chinese and Japanese display titles, editorial age
and content notes, exact source hashes and per-book license notices. The official
sources declare public domain in the USA; this is not a worldwide copyright claim.
Original prose can be challenging for English learners and is not CEFR-certified.
Practice text preserves narrative and framing while omitting navigation, illustrations,
publishing apparatus and some non-narrative prefatory matter. Full downloaded source
HTML remains available for reference. See [the complete reading list, rights and import
workflow](docs/english-original-readers.md).

## Multilingual book titles

All 100 public books and 100 archived standalone records include `title_i18n` with `en`, `zh-CN` and `ja` display titles.
The existing English `title`, chapter text and original credits are unchanged.
See [the field contract and reproducible editing workflow](docs/book-titles.md).
Application integration is separate; this resource update does not deploy the site.

## Learning and typing prompts

The 16-prompt catalog preserves the original 3 built-ins and includes 13 focused
task templates. Six optional browsing groups make the collection easier to
choose from: conversation, vocabulary, reading/writing, grammar, children's
stories, and learning images. The original three are marked `core` starting
points; all other tasks, including email writing and grammar lessons, remain
individually selectable `optional` entries. These are recommendations, not an
automatic import selection. No prompt ID or existing body is removed by this
grouping update. Across all entries, there are 11 English learning prompts,
1 English passage typing prompt and 4 image generation prompts. Practical
role-play, vocabulary recall, grammar repair, reading, writing and two children's
story workflows each serve a different learning activity. Image tasks cover a
single vocabulary card, a labeled scene, spatial relationships and wordless story
sequences. Spelling tiles are an optional vocabulary-card layout, not a separate
task. Restricted-key, punctuation/number and typing-error-review drills have been
retired; the existing typing-article built-in already generates English passages
from a requested topic, level, approximate word count and genre.
All prompts include additive `title_i18n` and `prompt_i18n` maps for `en`, `zh-CN`
and `ja`, plus localized descriptions and group labels, selection recommendations,
task, output and placeholder metadata. Existing `name` and `prompt`
fields remain the English fallbacks. The three original built-ins remain unchanged;
the vocabulary card intentionally merges the former spelling-tile option.
Instruction translation does not change the target English practice language.
See [task selection, field contracts and local rendering](docs/prompts.md). Image entries are templates,
not generated images; a compatible consumer route is required. The current
application importer still uses the legacy English fields; it does not yet
preserve prompt translations, render variables, group choices, or route image
tasks. This resource-only update does not implement those application features
or deploy the site. See the documented importer compatibility audit before use.

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
tools/import_hf_readers.py   Pinned, license-checked short-reader importer
tools/import_gutenberg_readers.py  Offline full-book importer with pinned sources
tools/gutenberg_readers.json  96 reviewed editions, titles and chapter inventories
tools/hf_readers.json        Curated reading list and upstream checksums
tools/book_titles.json       English, Chinese and Japanese book display titles
tools/story_anthology.py     Shared-body anthology and reversible old/new ID mapping
catalogs/standalone-readers.json  Preserved short-reader records, not public listings
tools/rebuild_prompts.py     Offline prompt validation, rendering and catalog rebuild
tests/                      Offline importer and prompt regression tests
docs/                       Hosting, frontend integration and rights notes
```

All catalog paths are relative to this repository root. Resolve them against
the manifest directory, rather than against the website's origin.
`manifest.json` covers the payloads and supporting files; it excludes itself.
Its file inventory is compact; optional per-file source audit data lives in a
deduplicated sidecar. Dictionary titles include English, Chinese and Japanese.
See [compact manifest and dictionary titles](docs/compact-manifest.md).
It contains no API keys, credentials, private user content or user progress.

## Verify locally

Python 3 is sufficient; no npm installation or backend is needed.

```sh
python3 tools/import_gutenberg_readers.py --check
python3 tools/rebuild_prompts.py --check
python3 tools/verify.py
python3 -m unittest discover -s tests -v
```

The validator checks every recorded file's size and SHA-256, dictionary entry
counts, anthology/archive mappings, per-story credits, chapter references, prompt files, model dependencies and the default
profile. This validates a resource repository, not a running TypeBook application.

## Recommended distribution

The full resource set is approximately 343 MiB. Live2D files account for about
211 MiB. The suggested default profile is about 102 MiB including the existing
browser runtimes: all books, dictionaries, prompts and demo/starter texts, plus
the Yuki model. Original Gutenberg HTML audit sources are retained in the full
repository but excluded from the default practice bundle. The other seven models can be loaded on demand.

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
