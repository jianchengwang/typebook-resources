# Short English readers from Hugging Face

This selection adds 16 real children's stories for English reading and typing:
3,741 words in total, from 21 to 564 words per story. Each original story is one
book and one complete chapter; its page breaks become paragraph breaks.
There are 176 original page paragraphs across the selection.

The four practice bands below are editorial suggestions, not certified CEFR
levels. Start with **starter**, then move to **easy**, **developing** and **longer**.
Texts retain their original cultural context, proper names and British-English
spelling. They are not rewritten or AI-generated stories.

## Reading list

| Band | Title | Words | Text author | License |
| --- | --- | ---: | --- | --- |
| starter | [Fire](../books/asp-fire/chapters/001.txt) | 21 | Deborah Namugosa, Beatrice Nabune, Alison Tukei, Rose Sabano | [CC-BY-3.0](https://creativecommons.org/licenses/by/3.0/) |
| starter | [What are you doing?](../books/asp-what-are-you-doing/chapters/001.txt) | 25 | Nina Orange | [CC-BY-3.0](https://creativecommons.org/licenses/by/3.0/) |
| starter | [I like to read!](../books/asp-i-like-to-read/chapters/001.txt) | 45 | Letta Machoga | [CC-BY-3.0](https://creativecommons.org/licenses/by/3.0/) |
| starter | [Counting animals](../books/asp-counting-animals/chapters/001.txt) | 74 | Zanele Buthelezi, Thembani Dladla, Clare Verbeek | [CC-BY-3.0](https://creativecommons.org/licenses/by/3.0/) |
| easy | [A very tall man](../books/asp-a-very-tall-man/chapters/001.txt) | 79 | Cornelius Gulere | [CC-BY-3.0](https://creativecommons.org/licenses/by/3.0/) |
| easy | [Zama is great!](../books/asp-zama-is-great/chapters/001.txt) | 127 | Michael Oguttu | [CC-BY-3.0](https://creativecommons.org/licenses/by/3.0/) |
| easy | [Tom the banana seller](../books/asp-tom-the-banana-seller/chapters/001.txt) | 140 | Humphreys Odunga | [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) |
| easy | [Goat, Dog, and Cow](../books/asp-goat-dog-and-cow/chapters/001.txt) | 148 | Fabian Wakholi | [CC-BY-3.0](https://creativecommons.org/licenses/by/3.0/) |
| easy | [Khalai talks to plants](../books/asp-khalai-talks-to-plants/chapters/001.txt) | 163 | Ursula Nafula | [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) |
| easy | [Decision](../books/asp-decision/chapters/001.txt) | 185 | Ursula Nafula | [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) |
| developing | [Anansi and Wisdom](../books/asp-anansi-and-wisdom/chapters/001.txt) | 285 | Ghanaian folktale | [CC-BY-3.0](https://creativecommons.org/licenses/by/3.0/) |
| developing | [A Tiny Seed: The Story of Wangari Maathai](../books/asp-a-tiny-seed-the-story-of-wangari-maathai/chapters/001.txt) | 412 | Nicola Rijsdijk | [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) |
| developing | [The day I left home for the city](../books/asp-the-day-i-left-home-for-the-city/chapters/001.txt) | 442 | Lesley Koyi, Ursula Nafula | [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) |
| longer | [What Vusi's sister said](../books/asp-what-vusis-sister-said/chapters/001.txt) | 503 | Nina Orange | [CC-BY-3.0](https://creativecommons.org/licenses/by/3.0/) |
| longer | [Grandma's bananas](../books/asp-grandmas-bananas/chapters/001.txt) | 528 | Ursula Nafula | [CC-BY-3.0](https://creativecommons.org/licenses/by/3.0/) |
| longer | [Holidays with grandmother](../books/asp-holidays-with-grandmother/chapters/001.txt) | 564 | Violet Otieno | [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) |

## Provenance and rights

- Dataset: [cis-lmu/GlotStoryBook](https://huggingface.co/datasets/cis-lmu/GlotStoryBook).
- Pinned dataset revision: `ad913a24f4a912cc0cd49a5f69e2055eba483d1f`.
- CSV SHA-256: `ffaeebc98583f3239b9dcebf6cf228aefbfe51435734a2b02c7a8c9792d3975e`.
- Original English texts: [global-asp/asp-source](https://github.com/global-asp/asp-source/tree/b5c3d5b2266ad936e5f20fa878e839b32b02b4ba/en).
- Original source revision: `b5c3d5b2266ad936e5f20fa878e839b32b02b4ba`.

Only the selected stories with an individual CC BY 3.0 or CC BY 4.0 license are
redistributed. The dataset itself includes mixed licenses; a dataset-level
label does not override a story's copyright. The importer rejects NC or
unrecognized licenses, missing/duplicate pages, non-English records, mismatched
attribution and any disagreement between HF text and the original source.

Every book directory contains:

- `chapters/001.txt`: typing-ready plain text, with original paragraphs.
- `cover.svg`: an original typographic cover; no downloaded illustrations.
- `LICENSE.md`: all original contributor credits, license and source links.
- `source.json`: source IDs, pinned revisions, hashes, credit and change notes.
- `original.md`: the exact selected source Markdown, including notices.

Original illustration credits are retained only as part of those source
notices; the source artwork is not included. Page markers become paragraphs,
whitespace is normalized, and curly quotes/dashes become keyboard-friendly
punctuation. No story words are rewritten. Keep the attribution and license
files with redistributed text, and make the catalog credit/source information
available in reading interfaces.

## Run the importer

Python 3.9+ and the standard library are sufficient. No account, token, external
package or model is needed. Network mode downloads about 26 MB once, plus the
small original source files. The mixed-license CSV stays in a cache outside
the repository and is never committed.

```sh
# Preview after downloading and checking immutable source hashes:
python3 tools/import_hf_readers.py

# Apply all validated outputs:
python3 tools/import_hf_readers.py --write

# Re-run using the existing cache only; a second write changes nothing:
python3 tools/import_hf_readers.py --write --offline
python3 tools/import_hf_readers.py --check --offline

# Full resource checks and importer regression tests:
python3 tools/verify.py
python3 -m unittest discover -s tests -v
```

Default cache: `~/.cache/typebook-hf-readers`. Use `--cache-dir /some/outside/path`
to change it. `--offline` fails if any pinned source is absent or corrupted;
it never falls back to a mutable branch or silently replaces a checksum.
`--check` compares generated outputs without modifying the repository, while
the default mode is a dry run. All selected inputs are validated before writes. Files are fully staged and
backed up outside the resource tree first, the manifest is installed last, and
an error or normal interrupt rolls back the batch. After a hard interruption,
run `python3 tools/import_hf_readers.py --recover` to restore the recorded old
state; recovery refuses to overwrite files edited after the interruption.
This is a sequence of atomic file renames, not an atomic whole-directory swap,
so do not publish or serve the working tree while an import is running.

The importer updates book catalogs, counts, default-profile file sizes and the
manifest hashes together. Existing books, articles, dictionaries, models,
export provenance and source metadata are preserved. Stable book/chapter IDs
are reserved as `800000 + original four-digit story ID`. The importer refuses
ID collisions, removal of previously imported stories, or overwriting edited
story payloads. Unexpected local files (including `.tmp` files and symlinks) cause an error
instead of being silently included in the repository-wide manifest. Generated text is data, never executed code.

To extend the selection, edit `tools/hf_readers.json` only after reading the
story and checking its individual license, author, original English text and
upstream license-index entry. Add exact source hashes and counts, then rerun
the importer and checks. Do not bulk-import all rows with a permissive-looking
dataset label. Do not replace pinned revisions without reviewing the changes.

## Application integration

This is a resource repository, not a running application. Its catalog now has
19 books and 42 chapters. Each chapter supplies the current loader's flat
`license_url`, `license_label`, `source_url`, `attribution` and `adaptation_note`
fields as well as book-level provenance. The collection loader currently drops
`adaptation_note`, so the visible attribution also includes the change notice.
All source contributor roles, including original adapters and translators,
are retained; original illustration credits explicitly say the images are not
included. TypeBook's application currently pins a resource
commit; publishing this repository alone does not advance that application
pin or change the live website. App integration and deployment are separate.
