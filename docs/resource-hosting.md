# Resource hosting contract

## Repository is data, not an application

The root `manifest.json` has `schema_version: 1`, a source revision, catalog
locations and a file inventory. Each file entry includes a relative `path`,
`bytes`, `sha256`, a content type, category and available provenance.

Catalog entries preserve stable namespaced IDs such as `book:1`, `dict:22`,
`article:900001` and `live2d:1`. Legacy IDs are retained as metadata, not as a
requirement to run the former D1 database.

Book and dictionary `body` references contain the exact payload checksum.
Live2D `entrypoint`, `directory` and texture/motion references preserve their
relative directory structure and case.

## Source configuration examples

Bundled assets, after a future application integration:

```json
{
  "type": "static",
  "manifest": "/resources/manifest.json",
  "profile": "default"
}
```

Public GitHub repository, after creating and pushing the repository:

```json
{
  "type": "github",
  "owner": "jianchengwang",
  "repository": "typebook-resources",
  "ref": "<published-commit-sha>",
  "manifest": "manifest.json"
}
```

The corresponding raw-data pattern is:

```text
https://raw.githubusercontent.com/{owner}/{repository}/{commit}/manifest.json
```

An independently hosted directory:

```json
{
  "type": "manifest",
  "url": "https://assets.example.org/typebook/manifest.json"
}
```

These examples describe the resource-source contract. The application pins the
published repository to a specific commit; arbitrary source selection remains
a possible future setting.

## Host requirements

- Anonymous HTTPS file downloads for public catalogs and assets.
- Browser CORS permission when hosted on a different origin.
- Stable direct file URLs that preserve the folder hierarchy.
- JSON response bodies for catalogs, not a login page or download dialog.
- Correct binary delivery for `.moc3`, images, `.onnx` and `.wasm`.
- Sensible caching, with immutable versions or an explicit refresh strategy.

A cloud-drive share page is not automatically a file endpoint. Expiring signed
links, cookies, anti-hotlinking checks and missing CORS headers can prevent
browser use even when the file can be downloaded manually.

Do not put a GitHub personal access token into a public frontend to read a
private repository. The new public repository avoids that credential
requirement. API rate limits are another reason to fetch a versioned manifest
and its files rather than making a GitHub Contents API call for every asset.

## Validation requirements for an importer

1. Reject unsupported schema versions, duplicate IDs and invalid catalog shapes.
2. Only resolve safe relative resource paths against the selected manifest root.
   Reject absolute paths, traversal, credentials and unexpected URL schemes.
3. Enforce limits on catalog size, file size, dictionary entries and model files
   before allocating large buffers.
4. Check byte lengths and SHA-256 after downloading. Do not cache a failed or
   partial response as a successful resource.
5. Validate Live2D dependency paths; preserve case on case-sensitive hosts.
6. Sanitize rendered resource text. Importing a manifest must not grant it
   permission to execute JavaScript.
7. Store user data separately from read-only official resources.

`tools/verify.py` implements the offline repository integrity checks. A future
browser importer must implement its own safe URL resolution and download limits.

## Capacity notes and references

The largest current file is below 22 MB. The full catalog is about 259 MiB, and
individual payloads are ordinary Git blobs. There are no Git LFS pointer files
in this export. Reassess large binary handling if models or speech engines grow.

Official reference pages to check before selecting a delivery host:

- GitHub file and repository limits:
  https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
- Cloudflare Workers Static Assets limits:
  https://developers.cloudflare.com/workers/static-assets/platform/limits/
- MDN browser CORS requirements:
  https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS

Public raw URLs and browser access should be checked with each application
integration. Availability can differ between users' networks.
