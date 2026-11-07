# Learning and typing prompts

This catalog contains **16 prompts: 3 preserved built-ins and 13 task-specific
prompts**. Every entry has English, Simplified Chinese, and Japanese display
titles **and full prompt instructions**. Original English `name` and `prompt`
fields remain the English fallbacks. The three built-ins are unchanged; the
vocabulary-card body intentionally incorporates the former spelling-tile layout.
Instruction language and practice language are separate: choosing Chinese or
Japanese instructions still produces the English exercise, story, labels, or
conversation specified by that task. Variable defaults and descriptive metadata
remain in English.

The three existing modes already cover ordinary English conversation,
English-only conversation, and general level-targeted typing passages. The other
items are selected for distinct practical workflows, not multiple versions of
those modes. Across the catalog, categories total **11 English learning, 1 typing
practice, and 4 image generation** entries. The English learning total includes
the two conversation built-ins and nine task templates.

There is no new generic article template: `builtin-typing-article` already accepts
a topic, target CEFR level, approximate word count, and genre in the user's
request. These are existing request settings, not new `{{placeholders}}`; the
built-in's `variables` list remains empty. It returns clean English prose without
questions or commentary. Reading comprehension, summary practice, storybook
production, and interactive storytelling remain separate because their outputs
and learner actions differ. Vocabulary retrieval already covers spelling recall;
one image vocabulary-card template supports either a whole-word label or letter
tiles instead of offering near-duplicate picture-card tasks.

## Choose by task

### Preserved built-ins

| ID | Existing purpose |
| --- | --- |
| `builtin-typing-article` | A clean, original English passage for copy typing. |
| `builtin-english-companion` | Natural English conversation with optional gentle correction. |
| `builtin-english-only` | Concise conversation entirely in English. |

Their original `id`, `name`, `source_type`, `display_type`, `prompt`, and
`legacy_id` values are unchanged. No new record is assigned a legacy numeric ID.

### English learning tasks (9)

| ID | Input and situation | Distinct output / interaction |
| --- | --- | --- |
| `learn-everyday-roleplay` | A fictional everyday scenario and target level. | A turn-by-turn practical exchange, one complication, and a final feedback recap; no real booking or purchase. |
| `learn-vocabulary-recall` | Three to eight target words. | Meaning-to-word retrieval, a sentence attempt, hints, and later retries of missed words. |
| `learn-collocation-lab` | One word or phrase. | Natural word partners and contextual gap fills, followed by a short learner-written story. |
| `learn-grammar-repair` | One grammar point. | One explicitly labeled erroneous sentence at a time, a corrected retry, and a rule recap. Not copy-typing material. |
| `learn-reading-check` | A topic and target level. | A short passage followed by separate detail, inference, and explanation questions without answer spoilers. |
| `learn-summary-paraphrase` | A topic and target level. | A longer passage, a learner summary, feedback on meaning and concision, then a model answer after revision. |
| `learn-email-practice` | A fictional low-stakes writing scenario. | A recipient/purpose/detail brief, learner draft, tone and clarity feedback, then a model revision. Nothing is sent. |
| `learn-childrens-storybook` | Audience age range, English level, theme, 4-12 pages, target words, and a general illustration style. | A complete paginated story manuscript, character sheet, self-contained text-free illustration briefs, and a separate clean reading/typing copy. Text output, not generated images. |
| `learn-choose-your-story` | Audience age range, English level, theme, and 3-6 scenes. | One story scene at a time; typed A/B choices, copied choice sentences, or original actions change the next scene. A clean copy of the actual chosen path is available afterward on request. |

### Image generation tasks (4)

| ID | Input and situation | Distinct visual output |
| --- | --- | --- |
| `image-vocabulary-card` | One word, its concrete sense, a general style, and optional `label_layout`. | One isolated illustration with an exact English label: a whole word by default, or one ordered letter per tile. |
| `image-scene-vocabulary` | An everyday setting and two to four object labels. | An integrated scene with unambiguous object-to-label relationships, for description and contextual vocabulary. |
| `image-preposition-cards` | A small object and a box-like container with a lid. | Six consistent spatial relationships, for learning `in`, `on`, `under`, `next to`, `behind`, and `in front of`. |
| `image-story-sequence` | A fictional four-step story. | Four text-free panels, for learner-authored narration and typed sentences. |

For `image-vocabulary-card`, `label_layout` defaults to `word`. Use `letter-tiles`
for a picture with one letter per tile, ideally with a word of 3–6 lowercase
letters. An invalid layout falls back to `word` in the prompt instructions. This
is a layout option for the same vocabulary-card task, not another catalog entry.

### Retired IDs and migration

- `image-spelling-tiles`: use `image-vocabulary-card` with
  `label_layout=letter-tiles` for the former letter-tile layout.
- `typing-restricted-keys`, `typing-precision-copy`, and `typing-error-review`:
  retired without replacements. Restricted-key, punctuation/number, and
  typing-error-review drills are outside the requested practical learning scope.

Active catalogs, the default profile, and the manifest do not reference these
four retired IDs or their source files. Consumers should remove stale choices
when adopting this revision; the builder does not redirect old IDs automatically.
Git history retains the earlier versions so they can be restored deliberately if
needed. The preserved typing-article built-in is the existing passage-generation
workflow, not a replacement for the retired drills.

## Additive metadata contract

Both `prompts/<id>.json` and its entry in `catalogs/prompts.json` expose the same
metadata. The catalog omits the long `prompt` and `prompt_i18n` bodies and adds
`path`. Load that source file to get the selected language's complete instructions;
do not expect the catalog alone to carry prompt content.
For example (abridged):

```json
{
  "id": "image-vocabulary-card",
  "name": "Illustrated Vocabulary Card",
  "title_i18n": {
    "en": "Illustrated Vocabulary Card",
    "zh-CN": "插画单词卡",
    "ja": "イラスト単語カード"
  },
  "source_type": "official",
  "display_type": "chat",
  "category": "image-generation",
  "output_type": "image",
  "prompt_role": "user",
  "cefr_levels": ["A1", "A2", "B1"],
  "variables": [
    {"name": "word", "default": "apple", "description": "One English word to render exactly."}
  ],
  "path": "prompts/image-vocabulary-card.json"
}
```

- **`name`** remains the English fallback. **`title_i18n.en`** is exactly equal
  to it. Use `entry.title_i18n?.[locale] || entry.name` for `en`, `zh-CN`, or `ja`;
  fall back to `name` for an unsupported locale or an older entry.
- **`prompt`** is the English instruction fallback.
  **`prompt_i18n`** exists on each source file with exactly `en`, `zh-CN`, and `ja`.
  `prompt_i18n.en` is byte-for-byte equal as a string to `prompt`. The other two
  entries translate the whole instruction, preserving constraints, English
  output requirements, literal commands, section labels, and variable meanings.
  Select `source.prompt_i18n?.[locale] || source.prompt` before substitution.
  An unsupported locale or an older source lacking the map falls back to the
  original English prompt. Locale matching is exact; map aliases such as `zh`
  to `zh-CN` deliberately in the consumer if desired.
- **`description`** is a short English purpose statement. **`tags`** are stable
  English filter terms, not localized interface labels.
- **`category`** is `english-learning`, `typing-practice`, or `image-generation`.
- **`cefr_levels`** lists intended practice difficulties, not assessed levels,
  official certification, or a guarantee that a generated result meets CEFR.
- **`display_type`** keeps the existing `chat` / `reading` vocabulary. `reading`
  means output intended to be copied into a typing passage. Interactive learning,
  feedback, and image tasks use `chat`. This field does **not** select a model.
- **`output_type`** is `text` or `image`. Image tasks require an image-capable
  route. An older consumer ignoring this field will **not** automatically gain
  image generation; it should avoid offering image tasks until that route exists.
- **`prompt_role`** is `system` for the three original built-in mode definitions
  and `user` for the 13 standalone task templates. Use the existing conversation
  setup for built-ins. Do not install every new task as a system prompt.
- **`variables`** lists each `{{variable_name}}` used by the body, with a usable
  `default` and English `description`. Repeated occurrences use the same value.
  All declared variables must occur; undeclared or malformed tokens are rejected.
  Every localized body must contain the same placeholder names and occurrence
  counts as its English body. Names and default values are not translated.
  For example, `{{feedback_language}}` changes only the help/feedback language,
  not the exercise language. Choosing `ja` for instruction text does not silently
  change an English `feedback_language` default.
  New templates are copyable after substitution. Interactive templates then wait
  for the learner's actual answer instead of filling it in.

The file format remains compatible at the field level, but consumer adoption is
separate. This repository change does not edit TypeBook's importer, model
configuration, database, frontend, or live deployment. Consumers pinned to an
older commit must deliberately adopt the new commit and its manifest. Preserve
the localized maps and template metadata during that later import.

A consumer integration can keep its current English flow, then add locale
selection in this order:

1. Display `title_i18n[locale]` with `name` fallback when browsing the catalog.
2. Fetch the source JSON at `path`, preserving `prompt` and the full `prompt_i18n`
   map in storage. Do not turn translated instruction content into generated
   learning material or concatenate all three languages into one model request.
3. Select one instruction body using the fallback above, then replace every
   placeholder occurrence in one literal substitution pass with its supplied
   value or default. Do not
   translate placeholder names or evaluate them as code. Keep all existing
   application safety checks and treat input values as untrusted data.
4. Use `prompt_role` and `output_type` to choose the appropriate message role and
   model route. The localized body retains the original task's output-language
   requirements. In particular, English-only chat must still output only English.
5. Keep `display_type=chat` for both story tasks. A multi-section book package or
   interactive transcript is not directly suitable for a typing passage field;
   extract its separate Reading-only copy only after reviewing it.

No provider API call, translation service, or paid content generation is part of
this resource update. The localized bodies are versioned editorial source text.

## Copy and render locally

Replace the placeholders yourself, or use the standard-library renderer:

```sh
python3 tools/rebuild_prompts.py --render image-vocabulary-card
python3 tools/rebuild_prompts.py --render image-vocabulary-card --values '{"word":"pear","meaning":"a whole green pear"}'
python3 tools/rebuild_prompts.py --render image-vocabulary-card --values '{"word":"cat","meaning":"a small friendly cat","label_layout":"letter-tiles"}'
python3 tools/rebuild_prompts.py --render learn-childrens-storybook --locale zh-CN
python3 tools/rebuild_prompts.py --render learn-choose-your-story --locale ja --values '{"scene_count":"3"}'
python3 tools/rebuild_prompts.py --render learn-everyday-roleplay --values '{"scenario":"asking for directions in a museum","level":"B1","feedback_language":"简体中文"}'
```

`--locale` is available only with `--render`; omitting it selects English.
An unsupported locale falls back to the original English body. The repository
validator still requires all three translations on every current source record,
so missing or malformed current translations fail validation rather than passing
as a silent fallback. Older-consumer fallback is a separate integration behavior.

Rendering makes one literal substitution pass. It does not execute expressions,
recursively render values, call a model, upload data, or incur provider costs.
Unknown variables, blank/non-string values, and nested placeholder tokens are
rejected. These structural checks do not semantically validate arbitrary words,
counts, scenes, or learner content. Use the documented input constraints. Keep
variable values as untrusted task data, and retain the application's own safety
and privacy controls. Do not put private personal records or credentials into
practice inputs.

All new text tasks support sensible defaults. Feedback tasks allow a
`feedback_language` value while keeping the practice in English. Text-only
practice cannot hear pronunciation, inspect keystrokes, measure elapsed time,
or remember future sessions. Model instructions request particular lengths,
counts, spellings, and layouts; they do not guarantee compliance.

Image templates are **prompts, not generated images**. They do not claim support
from a particular provider, audio output, exact pixel dimensions, or print-ready
quality. Inspect every image before teaching or printing: check the subject,
spatial relation, word spelling, letter order, and label placement. Models may
misspell labels or draw the wrong relation. When lettering fails, use blank text
areas and add verified text with a deterministic editor. Use original generic
subjects and broad visual styles; no branded characters or named-artist copying
is needed for these exercises.

## Children's story workflows

These two tasks deliberately serve different purposes:

- **Storybook Builder** produces the complete book manuscript at once. It gives
  each page readable story text and a separate illustration brief; a shared
  character sheet and repeated visual anchors help later images stay consistent.
  The reading-only section repeats the page prose verbatim, without production
  notes, so it can be copied into a typing exercise. Unlike `image-story-sequence`,
  it writes a whole readable story rather than generating four wordless panels.
- **Choose Your Story** waits for the learner after every nonfinal scene. A/B,
  a copied choice sentence, and an original safe action are all valid inputs.
  Choices affect subsequent events; they are not comprehension questions with
  right answers. The final scene ends the story rather than adding another
  choice. `finish` closes the current path early, while `stop` pauses it. Feedback
  is optional, and no WPM or invented accuracy score is reported. This differs
  from practical role-play and from the existing read-and-answer exercise.

Both separate audience age from language proficiency, offer A1/A2/B1 writing
targets, and request original, gentle, non-identifying material. They must not
solicit a child's name, school, address, photos, or other identifying details.
Use only broad age ranges and fictional characters. Avoid copyrighted characters,
franchise settings, copied book passages, and named-author/artist imitation.
Instructions do not establish legal clearance or guarantee generated quality.
A parent or teacher should review the result before a child uses it.

The book builder's output is **text**, including image prompts, not a finished
illustrated book, PDF, or print-ready layout. A separate image-capable route is
needed to make pictures. Keep generated pictures text-free and typeset the
verified English separately: image models do not guarantee exact lettering or
character continuity. Check images, page ordering, word repetition, age suitability,
and the reading-only copy before teaching or publishing. Counts and input ranges
are prompt instructions; the local renderer checks structure, not model behavior
or the semantic validity of a numeric string. The templates describe safe defaults
for invalid age/level/count settings instead of requesting identifying details.

## Editing, validation, and reproducibility

The **individual prompt JSON files are the editorial source of truth**. Edit
those files, not a duplicate translation list. Then run:

```sh
python3 tools/rebuild_prompts.py --write
python3 tools/rebuild_prompts.py --check
python3 tools/import_hf_readers.py --check --offline
python3 tools/verify.py
python3 -m unittest discover -s tests -v
```

The prompt builder performs no network access. The book check uses its existing
pinned input cache; omit that optional cross-check if the cache is unavailable,
or prepare it through the documented reader import workflow. A no-op book import
does not reset the manifest revision belonging to a later prompt update.

The builder preserves existing catalog order, appends new IDs deterministically,
updates the prompt count and default profile, and recalculates manifest checksums
and byte totals. It refuses undeclared removals, symlinked sources, and unexpected
local files that could accidentally publish private material. The default mode
reports changes without writing. Ordinary edits and no-op rebuilds need no
retirement flags; repeated `--write` and `--check` runs remain the normal workflow.
Generated files use the existing staged write/backup/recovery mechanism; do not
serve or commit a partially updated working tree. After an interrupted write,
inspect the error and use `python3 tools/rebuild_prompts.py --recover` as directed.

### Explicit retirement workflow

Retirement is an opt-in editorial action, not a side effect of rebuilding. First
remove **only the authorized tracked source files** from `prompts/`. The builder
never deletes source files itself. Then declare each retired ID with a repeatable
`--remove-prompt` flag, preview the changes, and write with the same flags:

```sh
# After removing the four authorized source files, preview without writing:
python3 tools/rebuild_prompts.py --remove-prompt typing-restricted-keys --remove-prompt typing-precision-copy --remove-prompt typing-error-review --remove-prompt image-spelling-tiles
# Apply the same declared retirement:
python3 tools/rebuild_prompts.py --remove-prompt typing-restricted-keys --remove-prompt typing-precision-copy --remove-prompt typing-error-review --remove-prompt image-spelling-tiles --write
# Return to the normal check (no retirement flags):
python3 tools/rebuild_prompts.py --check
```

These commands describe this revision's migration from the earlier catalog; do
not repeat the retirement flags after the IDs have already been removed. The
builder refuses undeclared removals, declarations whose source files are still
present, unknown or duplicate IDs, built-in removals, and unrelated removed files.
A successful retirement updates the catalog, profile, manifest, and counts
without erasing history or touching unrelated resources.

Tests cover preserved built-in fields, localized titles and bodies,
source/catalog consistency, image/text routing metadata, placeholder parity across
languages, localized rendering and fallback, story task contracts, vocabulary-card
layouts, explicit retirement safeguards, variable rendering and rejection cases,
accidental file inclusion, stable ordering, preservation, and repeatable generation.
`verify.py` checks all manifest payload hashes and profile references. These are
offline structural/content-contract tests, not live model quality, image-rendering,
browser, or deployment tests. Review content changes for practical usefulness and
duplication separately from automated validation.
