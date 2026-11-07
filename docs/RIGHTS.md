# Resource provenance and rights

This catalog preserves the resources already configured as official in the
TypeBook installation, plus existing frontend public assets.

"Official" is an application catalog classification, not a copyright license.
This repository does not grant a new blanket license over third-party texts,
dictionaries, Live2D models, Cubism components, images or browser runtimes.

## Recorded attribution

- Demo anthology attribution and copy policy are preserved in the article
  catalog.
- The original three book titles and authors are preserved. The source database did not supply
  edition-specific license metadata for those original records.
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

The 100 `books/asp-*/` additions are English African Storybook texts obtained
through `cis-lmu/GlotStoryBook` on Hugging Face. Each story was checked against
its original English Markdown and its own license entry in the upstream index.
The first 16 also had publication credits checked on Storybooks Canada;
the later 81 were individually reviewed against the fixed originals, with
additional current publisher notices retained separately where supplied. They are licensed
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

## Original learning prompt additions (November 2026)

The 15 new learning, typing and image-generation templates, their descriptions,
and all prompt display-title translations were newly authored for this catalog,
not copied from third-party prompt collections. Original built-in prompt values
remain unchanged. This addition does not relicense any existing resource or
assert blanket rights over model-generated output. The image entries contain
text templates only, not third-party illustrations or generated image assets.
See [prompt usage and verification notes](prompts.md).

The children's anthology references the existing story bodies without rewriting
or copying them. Each story keeps its own license and notices. Combined credits
are in `books/childrens-short-stories/LICENSE.md`; standalone records remain in
`catalogs/standalone-readers.json` for compatibility.

## English-original children and youth readers

The 96 new Project Gutenberg editions carry per-book source pages, SHA-256 pins,
original HTML and full source license text. Each official page explicitly declares
public domain in the USA. This is a jurisdiction-specific designation, not a
worldwide license or a conclusion based solely on noncommercial use. See
[selection and rights review](english-original-readers.md). No source illustrations
or publisher covers are used as practice assets. The new SVG covers and localized
display labels do not license unrelated translated editions. Existing resource
rights are unchanged.
