# Frontend resource assessment

Assessment date: November 2, 2026.

Publication decision: the user selected the public resource repository as the
application's default official source. The bundling recommendation below is
retained as an alternative distribution strategy. Application integration pins
a commit, fetches resources on demand and verifies catalog/text checksums.

## Recommendation

Maintain the complete catalog in this independent resource repository. Bundle
the default profile in `frontend/public/resources/` when implementing the next
application resource adapter. Keep additional Live2D models optional.

The small text resources do not justify a database/API request for every read.
The eight models, however, total 221,522,983 bytes, and Aniya plus Huohuo make up
most of that size. Bundling all models is technically possible but increases
clones, builds and deployments even for users who only use Yuki.

These are file sizes, not the compressed Git transfer size or the first-page
download size. Existing browser runtime assets are included in the default
profile's total, and are already part of the application today.

| Approach | Benefits | Costs | Proposed role |
| --- | --- | --- | --- |
| Frontend static directory | Same-origin access, reproducible deployment, works without a content API | Updating content requires rebuilding or copying static files | Default texts, dictionaries, prompts and Yuki |
| Public GitHub resource repository | Separate history, configurable source, optional updates | Network availability, cross-origin delivery, changing branch contents | Optional models and resource updates |
| Arbitrary HTTPS directory | Flexible storage and mirrors | Host must support direct file reads and browser CORS | Advanced user-selected source |
| Existing Cloudflare objects | Already operational | Current object routes still use the business Worker | Retained existing source during migration |

## Migration sequence

1. Add a resource-source interface that provides collection, book, article,
   dictionary, prompt and model catalogs from a versioned manifest.
2. Implement bundled-static and remote-manifest adapters. Preserve the current
   API adapter until local reading and import flows work.
3. Resolve and validate relative paths, IDs, counts, checksums, payload types
   and resource limits. Choose the default profile before resolving optional
   models. A full model catalog includes entries absent from a smaller bundle.
4. Cache completed downloads in IndexedDB or Cache Storage, partitioned by
   manifest revision and resource SHA-256. Retain a usable bundled default when
   an optional source fails.
5. Save personal collections, imported EPUB chapters, dictionaries, favorites,
   wrong words, progress and AI results in browser storage. Provide explicit
   export/import for migration between browsers and devices.
6. Add user settings for an optional manifest URL or repository reference.
   Repository downloads supply data and model assets; do not execute arbitrary
   scripts referenced by a user-selected manifest.
7. Test guest startup with the business API unavailable. Current demo texts,
   built-in prompts and fallback Yuki assets are a partial foundation, but
   today's dictionary/book lists and many persistence paths still call APIs.
8. Keep the existing Cloudflare deployment and resources available until the
   new adapters and local persistence have been verified.

This export implements the resource catalog and integrity checks only. It does
not implement steps 1-8 in the application, and does not switch production.

## Meaning of "without a backend"

Static resources and local user data can work entirely in the browser. Email
login, account synchronization, shared collections, server-managed quotas and
administration need either a service or a redesigned local-only workflow.
Private resources should stay in account-scoped local storage, never in this
public resource catalog.

AI also has a separate constraint. Moving dictionaries and models does not
change a provider's CORS policy. Direct browser access only works when the
selected provider supports it. A provider that rejects the browser preflight,
including the previously reported Zhipu endpoint, still requires a compatible
relay, a user-operated local service, or choosing a provider that allows direct
browser requests. API credentials must remain user settings and must not enter
this resource repository or a frontend build.

Browser storage has device-specific quotas and may be cleared by the browser.
Offline use needs an explicit cache/download flow; placing files in `public/`
alone does not make the application work offline.

## Publication and fallback

Keep the application repository private. A new public resource repository can
serve anonymous readers after publication, subject to its delivery host's
availability and browser response headers. Publishing the repository is not
the same as validating a particular browser, CDN, mirror or network.

Recommended source priority:

1. Selected source's already verified cached file.
2. Bundled default resources for ordinary startup.
3. A configured remote manifest for optional resources and explicit updates.

Do not silently change a resource's edition, checksum or ID to mask a failed
download. Present a retry or let the user choose another source. Continue to
retain Cloudflare objects during this migration.
