# Resource provenance and rights

This catalog preserves the resources already configured as official in the
TypeBook installation, plus existing frontend public assets.

"Official" is an application catalog classification, not a copyright license.
This repository does not grant a new blanket license over third-party texts,
dictionaries, Live2D models, Cubism components, images or browser runtimes.

## Recorded attribution

- Demo anthology attribution and copy policy are preserved in the article
  catalog.
- Book titles and authors are preserved. The source database did not supply
  edition-specific license metadata for these records.
- Existing dictionary names and descriptions are preserved. Missing license
  metadata is recorded as `not-recorded-in-source`.
- Live2D model names, internal notices and original files are preserved.
  Separate model redistribution licenses were not recorded in the exported
  database.
- The existing Paradee `LICENSE`, `NOTICE.md` and `provenance.json` are retained
  together with its model.
- Existing notices embedded in JavaScript and other runtime files remain intact.

Before public distribution, establish and record any missing permissions or
source-specific restrictions. Do not interpret an absent license as a grant of
unrestricted use. Add explicit licenses only where the applicable rights and
terms have been established.

## Scope of the export

Only official/public resource records and their registered public object files
were read from the current Cloudflare deployment. Frontend defaults were
extracted from the application's current source and public directory.

The resource directory excludes accounts, profile data, authentication material,
API keys, private content, user collections, practice history and saved learning
items. Source database metadata used internally to prepare the export is not
part of this publishable directory.

No Cloudflare object or database resource was deleted or changed during export.

## Individually licensed Hugging Face readers (November 2026)

The 16 `books/asp-*/` additions are English African Storybook texts obtained
through `cis-lmu/GlotStoryBook` on Hugging Face. Each story was checked against
its original English Markdown and its own license entry in the upstream index,
with publication credits also checked on Storybooks Canada. They are licensed
CC BY 3.0 or CC BY 4.0, as identified per book.

Each folder includes `LICENSE.md` (attribution and license link), `source.json`
(immutable source revision, SHA-256, original links and transformation notes),
and the selected original Markdown with its notices. Practice text changes are
limited to whitespace, page-to-paragraph layout and keyboard-friendly quotation
marks/dashes. No source illustrations are distributed. The SVG covers are
new typographic designs, not copies of the source artwork.

The Hugging Face dataset contains mixed licenses, including noncommercial
material. Its top-level metadata is not treated as permission for every story.
Only the explicitly curated CC BY texts are included; the full CSV is not
redistributed. This does not change the rights status of pre-existing assets.

See [the import documentation](huggingface-readers.md) for the full reading list
and reproducibility instructions.
