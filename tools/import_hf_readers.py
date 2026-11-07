#!/usr/bin/env python3
"""Import a curated, pinned, individually licensed GlotStoryBook reading list.

Python standard library only. Downloads are cached outside this repository.
The default is a dry run; --write applies the plan and --check checks it offline.
"""
import argparse
import csv
import hashlib
import html
import io
import json
import pathlib
import re
import shutil
import signal
import os
import sys
import textwrap
import unicodedata
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "tools/hf_readers.json"
SUPPORT_FILES = {"tools/import_hf_readers.py", "tools/hf_readers.json",
                 "tests/test_import_hf_readers.py", "docs/huggingface-readers.md"}
LICENSES = {
    "CC-BY-3.0": "https://creativecommons.org/licenses/by/3.0/",
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
}
CHANGES = "Page breaks become paragraphs; whitespace and curly quotes/dashes are normalized for keyboard practice. No words are rewritten. Original illustrations are not included."


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def safe_path(root, relative):
    require(isinstance(relative, str) and relative, "Missing path")
    require(not re.search(r"[\\:%\x00]", relative), "Unsafe path: " + relative)
    parts = pathlib.PurePosixPath(relative)
    require(not parts.is_absolute() and ".." not in parts.parts, "Unsafe path: " + relative)
    path = root / relative
    require(path.resolve().is_relative_to(root.resolve()), "Path escapes repository: " + relative)
    return path


def normalize(text):
    text = unicodedata.normalize("NFC", text).translate(str.maketrans({
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u00a0": " ",
    }))
    return re.sub(r"\s+", " ", text).strip()


def download(url, expected_sha, cache, offline, max_bytes):
    require(re.fullmatch(r"[0-9a-f]{64}", expected_sha), "Invalid source SHA-256")
    target = cache / expected_sha
    require(not target.is_symlink(), "Symlinked cache file")
    if target.exists():
        data = target.read_bytes()
    else:
        require(not offline, "Missing cached source: " + url)
        request = urllib.request.Request(url, headers={"User-Agent": "TypeBook-resource-importer/1"})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(max_bytes + 1)
        require(len(data) <= max_bytes, "Source exceeds size limit: " + url)
        require(sha256(data) == expected_sha, "Source checksum mismatch: " + url)
        cache.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
    require(len(data) <= max_bytes and sha256(data) == expected_sha, "Invalid cached source: " + url)
    return data


def parse_story(raw):
    text = raw.decode("utf-8-sig").replace("\r\n", "\n")
    parts = re.split(r"^##\s*$", text, flags=re.MULTILINE)
    require(parts[0].strip().startswith("# "), "Missing source title")
    metadata = dict(re.findall(r"^\* ([^:]+):\s*(.*)$", parts[-1], flags=re.MULTILINE))
    require(metadata.get("Language") == "en", "Non-English original")
    require(metadata.get("License") in ("[CC-BY]", "[CC BY]"), "Original license is not CC BY")
    paragraphs = [normalize(p) for p in parts[1:-1] if p.strip()]
    require(paragraphs, "Empty original")
    return parts[0].strip()[2:], paragraphs, metadata


def validate_selection(config):
    require(config["schema_version"] == 1, "Unsupported selection schema")
    require(config["dataset"]["repository"] == "cis-lmu/GlotStoryBook", "Unsupported dataset")
    require(config["upstream"]["repository"] == "global-asp/asp-source", "Unsupported upstream")
    for source in (config["dataset"], config["upstream"]):
        require(re.fullmatch(r"[0-9a-f]{40}", source["revision"]), "Source must use an immutable commit")
    for key in ("slug", "legacy_id", "chapter_legacy_id", "parallel_id", "filename"):
        values = [item[key] for item in config["books"]]
        require(len(set(values)) == len(values), "Duplicate selected " + key)
    for book in config["books"]:
        require(re.fullmatch(r"asp-[a-z0-9-]+", book["slug"]), "Invalid book slug")
        require(re.fullmatch(r"[0-9]{4}_[a-z0-9][a-z0-9_.-]*\.md", book["filename"]) and ".." not in book["filename"], "Invalid source filename")
        code = book["filename"][:4]
        require(book["parallel_id"] == "asp_" + code, "Source story ID disagreement")
        require(book["legacy_id"] == book["chapter_legacy_id"] == 800000 + int(code), "Reserved stable ID disagreement")
        require(re.fullmatch(r"[0-9a-f]{64}", book["source_sha256"]), "Invalid source SHA-256")
        require(book["practice_band"] in ("starter", "easy", "developing", "longer"), "Unknown practice band")
        require(all(isinstance(book[k], str) and book[k].strip() for k in ("title", "author", "practice_note")), "Missing editorial metadata")
        for notice in book.get("additional_attribution", []):
            require(isinstance(notice.get("text"), str) and notice["text"].strip(), "Empty publisher notice")
            require(isinstance(notice.get("evidence_url"), str) and notice["evidence_url"].startswith("https://"), "Missing publisher notice evidence")
        require(book["license_id"] in LICENSES and LICENSES[book["license_id"]] == book["license_url"], "Unapproved license")
        require(all(isinstance(book[k], int) and book[k] > 0 for k in ("legacy_id", "chapter_legacy_id", "paragraph_count", "word_count")), "Invalid numeric selection field")


def cover(book):
    lines = textwrap.wrap(book["title"], width=22)
    title = "\n".join(f'<text x="48" y="{200+i*45}" font-size="33" font-weight="700">{html.escape(line)}</text>' for i, line in enumerate(lines))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="640" viewBox="0 0 480 640">\n'
            f'<rect width="480" height="640" fill="#f7f3e9"/><rect x="0" y="0" width="16" height="640" fill="#397864"/>\n'
            f'<g font-family="sans-serif" fill="#233d35"><text x="48" y="75" font-size="16" letter-spacing="2">ENGLISH SHORT READERS</text>\n{title}\n'
            f'<path d="M48 490h80m-40-40v80" stroke="#397864" stroke-width="5"/><text x="48" y="580" font-size="16">{book["word_count"]} words · {html.escape(book["practice_band"])}</text></g>\n</svg>\n').encode()


def body_ref(path, data):
    return {"path": path, "sha256": sha256(data), "bytes": len(data)}


def build_books(config, dataset_bytes, index_bytes, originals):
    """Fail closed on license, language, attribution, order, or source disagreement."""
    validate_selection(config)
    groups = {book["parallel_id"]: [] for book in config["books"]}
    for row in csv.DictReader(io.StringIO(dataset_bytes.decode("utf-8-sig"))):
        if row["Parallel ID"] in groups and row["ISO639-3"] == "eng" and row["Source"] == config["upstream"]["repository"]:
            groups[row["Parallel ID"]].append(row)
    index = index_bytes.decode("utf-8-sig")
    books, files = [], {}
    seen_texts = {}
    for selected in config["books"]:
        rows = groups[selected["parallel_id"]]
        require(len(rows) == selected["paragraph_count"], "Missing or duplicate pages: " + selected["slug"])
        require(all(row["License"] in ("CC-BY", "CC BY") and row["Language"] == "en" and row["File Name"] == selected["filename"] and row["Text By"] == selected["author"] for row in rows), "Dataset metadata disagreement: " + selected["slug"])
        rows.sort(key=lambda row: int(row["Text Number"]))
        require([int(row["Text Number"]) for row in rows] == list(range(len(rows))), "Nonsequential or duplicate pages")
        paragraphs = [normalize(row["Text"]) for row in rows]
        require(all(paragraphs), "Empty dataset page")
        title, original_paragraphs, meta = parse_story(originals[selected["filename"]])
        require(title == selected["title"] and meta["Text"] == selected["author"], "Original attribution mismatch")
        require(paragraphs == original_paragraphs, "Dataset differs from original: " + selected["slug"])
        fingerprint = normalize(" ".join(paragraphs)).casefold()
        require(fingerprint not in seen_texts, "Duplicate story text: " + selected["slug"] + " / " + seen_texts.get(fingerprint, ""))
        seen_texts[fingerprint] = selected["slug"]
        code = selected["filename"][:4]
        lines = [line for line in index.splitlines() if line.startswith(code + " |")]
        require(len(lines) == 1, "Missing or ambiguous license evidence")
        links = re.findall(r"\[([^]]+)\]\(([^)]+)\)", lines[0])
        require(len(links) == 2 and links[1][0] in ("CC-BY", "CC BY") and links[1][1] == selected["license_url"] and links[0][1] == selected["original_url"], "Original index license disagreement")
        text = ("\n\n".join(paragraphs) + "\n").encode()
        require(len(text.decode().split()) == selected["word_count"], "Unexpected word count")
        folder = "books/" + selected["slug"]
        chapter_path, cover_path = folder + "/chapters/001.txt", folder + "/cover.svg"
        files[chapter_path], files[cover_path] = text, cover(selected)
        upstream = config["upstream"]
        source_url = f'https://github.com/{upstream["repository"]}/blob/{upstream["revision"]}/en/{selected["filename"]}'
        index_url = f'https://github.com/{upstream["repository"]}/blob/{upstream["revision"]}/{upstream["index_path"]}'
        provenance = {
            "import_id": config["import_id"], "title": title, "author": selected["author"],
            "translator": meta.get("Translated By") or meta.get("Translation") or None, "adaptation": meta.get("Adaptation") or None,
            "original_illustrator": meta.get("Illustration") or None, "original_metadata": meta, "language": "en",
            "license": {"id": selected["license_id"], "url": selected["license_url"]},
            "original_url": selected["original_url"], "reader_url": selected.get("reader_url", selected["original_url"]),
            "verification_url": selected.get("verification_url"), "upstream_text_url": source_url,
            "upstream_sha256": selected["source_sha256"], "license_evidence_url": index_url,
            "license_evidence_line": lines[0], "dataset": {**config["dataset"], "parallel_id": selected["parallel_id"], "filename": selected["filename"]},
            "changes": CHANGES, "cover": "Original typographic SVG generated by this importer; no source illustrations used.",
            "practice": {"band": selected["practice_band"], "note": selected["practice_note"], "certified_cefr_level": None},
        }
        if selected.get("additional_attribution"):
            provenance["additional_attribution"] = selected["additional_attribution"]
        files[folder + "/source.json"] = json_bytes(provenance)
        # Keep the selected original only, never the mixed-license full dataset.
        files[folder + "/original.md"] = originals[selected["filename"]]
        credit_parts = []
        for role, name in meta.items():
            if role in ("License", "Language") or not name:
                continue
            label = {"Translated By": "Translation", "Adaptation": "Original adaptation", "Illustration": "Original illustrations (not included)"}.get(role, role)
            credit_parts.append(f"{label}: {name}.")
        for notice in selected.get("additional_attribution", []):
            credit_parts.append(f'Additional publisher notice: {notice["text"]} Evidence: {notice["evidence_url"]}')
        attribution = " ".join(credit_parts)
        credit = f"# {title}\n\n" + "\n".join(credit_parts) + "\n"
        credit += (f'\nText licensed under [{selected["license_id"]}]({selected["license_url"]}).\n'
                   f'[Original story]({selected.get("reader_url", selected["original_url"])}) · [Source text]({source_url}) · [License evidence]({index_url}).\n\n'
                   f'Imported through [cis-lmu/GlotStoryBook](https://huggingface.co/datasets/cis-lmu/GlotStoryBook/tree/{config["dataset"]["revision"]}).\n\n'
                   f'{CHANGES}\n\nThe typographic cover is generated for TypeBook. Source illustration credits are retained in original.md, but those illustrations are not distributed here.\n'
                   'Practice bands are editorial suggestions, not tested CEFR ratings. See source.json for checksums and full provenance.\n')
        files[folder + "/LICENSE.md"] = credit.encode()
        bid, cid = selected["legacy_id"], selected["chapter_legacy_id"]
        books.append({
            "title": title, "author": selected["author"],
            "description": f'{selected["practice_note"]} A {selected["word_count"]}-word English reader from African Storybook, imported through GlotStoryBook. Text by {selected["author"]}; {selected["license_id"]}: {selected["license_url"]} Source: {source_url}',
            "tags": json.dumps(["english-learning", "short-readers", "typing-practice", selected["practice_band"]]),
            "word_count": selected["word_count"], "chapter_count": 1, "revision": 1,
            "id": f"book:{bid}", "legacy_id": bid, "license_status": "verified-cc-by",
            "license": provenance["license"], "source": {"import_id": config["import_id"], "path": folder + "/source.json"},
            "cover": body_ref(cover_path, files[cover_path]),
            "chapters": [{"book_id": bid, "title": title, "chapter_number": 1, "word_count": selected["word_count"], "revision": 1,
                          "id": f"chapter:{cid}", "legacy_id": cid,
                          "source_url": provenance["reader_url"], "license_url": selected["license_url"], "license_label": selected["license_id"],
                          "attribution": attribution + f' African Storybook. Source: {provenance["reader_url"]} ' + CHANGES,
                          "adaptation_note": CHANGES, "body": body_ref(chapter_path, text)}],
        })
    return books, files


def resource_files(root):
    return sorted(path for path in root.rglob("*") if (path.is_file() or path.is_symlink()) and not set(path.relative_to(root).parts) & {".git", "__pycache__"} and path.name not in ("manifest.json", ".DS_Store"))


def make_plan(root, config, new_books, outputs):
    outputs = dict(outputs)
    old_manifest = json.loads((root / "manifest.json").read_text())
    recorded = {item["path"]: item for item in old_manifest["files"]}
    existing = json.loads((root / "catalogs/books.json").read_text())
    selected_ids = {book["id"] for book in new_books}
    owned = [book for book in existing if book.get("source", {}).get("import_id") == config["import_id"]]
    require({book["id"] for book in owned} <= selected_ids, "Removing previously imported books is not supported")
    unrelated = [book for book in existing if book not in owned]
    require(not selected_ids & {book["id"] for book in unrelated}, "Book ID collision")
    new_chapter_ids = {chapter["id"] for book in new_books for chapter in book["chapters"]}
    require(not new_chapter_ids & {chapter["id"] for book in unrelated for chapter in book["chapters"]}, "Chapter ID collision")
    owned_folders = {str(pathlib.PurePosixPath(book["source"]["path"]).parent) + "/" for book in owned}
    for relative, data in outputs.items():
        path = safe_path(root, relative)
        if path.exists() and path.read_bytes() != data:
            require(any(relative.startswith(folder) for folder in owned_folders), "Refusing to overwrite existing file: " + relative)
            require(relative in recorded and sha256(path.read_bytes()) == recorded[relative]["sha256"], "Locally edited imported file: " + relative)
    # Preserve existing ordering and append new readers in curated order.
    replacements = {book["id"]: book for book in new_books}
    books = [replacements.get(book["id"], book) for book in existing]
    books.extend(book for book in new_books if book["id"] not in {b["id"] for b in existing})
    outputs["catalogs/books.json"] = json_bytes(books)
    summary = json.loads((root / "catalogs/summary.json").read_text())
    summary.update(books=len(books), chapters=sum(book["chapter_count"] for book in books))
    outputs["catalogs/summary.json"] = json_bytes(summary)
    profile = json.loads((root / "profiles/default.json").read_text())
    profile["books"] = list(dict.fromkeys(profile["books"] + [book["id"] for book in new_books]))
    profile["files"] = sorted(set(profile["files"]) | {p for p in outputs if p.startswith("books/")})
    profile["payload_bytes"] = sum(len(outputs[p]) if p in outputs else safe_path(root, p).stat().st_size for p in profile["files"])
    outputs["profiles/default.json"] = json_bytes(profile)
    actual_paths = {p.relative_to(root).as_posix() for p in resource_files(root)}
    allowed_paths = set(recorded) | set(outputs) | SUPPORT_FILES
    unexpected = sorted(actual_paths - allowed_paths)
    require(not unexpected, "Unexpected local files; not adding them to manifest: " + ", ".join(unexpected))
    require(not any(p.endswith(".tmp") for p in actual_paths), "Temporary file found; refusing manifest update")
    all_paths = actual_paths | set(outputs)
    files = []
    for relative in sorted(all_paths):
        path = safe_path(root, relative)
        require(not path.is_symlink(), "Symlinked resource: " + relative)
        data = outputs[relative] if relative in outputs else path.read_bytes()
        entry = dict(recorded.get(relative, {}))
        entry.update(path=relative, bytes=len(data), sha256=sha256(data))
        if "content_type" not in entry:
            entry["content_type"] = {".md": "text/markdown", ".py": "text/x-python", ".json": "application/json", ".txt": "text/plain", ".svg": "image/svg+xml"}.get(path.suffix, "application/octet-stream")
        if "category" not in entry:
            entry["category"] = "book" if relative.startswith("books/") else "documentation" if relative.startswith("docs/") else "tooling"
        if relative.startswith("books/") and relative in outputs:
            entry["source"] = {"kind": "curated-huggingface-import", "import_id": config["import_id"], "provenance": str(pathlib.PurePosixPath(relative).parents[1] if "/chapters/" in relative else pathlib.PurePosixPath(relative).parent) + "/source.json"}
        files.append(entry)
    manifest = dict(old_manifest)
    manifest.update(revision=config["revision"], counts=summary, files=files, total_bytes=sum(item["bytes"] for item in files))
    outputs["manifest.json"] = json_bytes(manifest)
    return outputs


def transaction_directory(root):
    return root.parent / ("." + root.name + "-hf-readers-transaction")


def save_journal(directory, journal):
    temporary = directory / "journal.tmp"
    with temporary.open("xb") as stream:
        stream.write(json_bytes(journal))
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(directory / "journal.json")


def recover_transaction(root):
    """Restore only files whose bytes still match this interrupted transaction."""
    directory = transaction_directory(root)
    require(directory.is_dir() and not directory.is_symlink(), "No recoverable transaction")
    journal = json.loads((directory / "journal.json").read_text())
    require(journal["root"] == str(root.resolve()), "Transaction belongs to a different repository")
    if journal["phase"] in ("committed", "preparing"):
        shutil.rmtree(directory)
        return
    # Validate every backup and current target before restoring anything.
    for item in journal["files"]:
        target = safe_path(root, item["path"])
        require(not target.is_symlink(), "Symlinked recovery target")
        current = sha256(target.read_bytes()) if target.exists() else None
        require(current in (item["old_sha256"], item["new_sha256"]), "File changed after interruption; refusing recovery: " + item["path"])
        if item["old_sha256"] is not None:
            backup = safe_path(directory / "old", item["path"])
            require(backup.is_file() and sha256(backup.read_bytes()) == item["old_sha256"], "Invalid recovery backup")
    for item in reversed(journal["files"]):
        target = safe_path(root, item["path"])
        if item["old_sha256"] is None:
            if target.exists():
                target.unlink()  # Only a new file with this transaction's exact bytes.
        else:
            backup = safe_path(directory / "old", item["path"])
            temporary = target.with_name(target.name + ".hf-restore.tmp")
            require(not temporary.exists(), "Existing recovery temporary file")
            with temporary.open("xb") as stream:
                stream.write(backup.read_bytes())
            temporary.replace(target)
    shutil.rmtree(directory)


def apply_plan(root, plan, changed, replace=None):
    """Stage and back up everything first; commit manifest last; roll back failures.

    The recovery journal also supports --recover after SIGKILL or machine shutdown.
    A commit consists of several atomic renames, not an atomic directory swap.
    Do not serve or commit the working tree until this command has completed.
    """
    if not changed:
        return
    directory = transaction_directory(root)
    require(not directory.exists(), "Interrupted import exists; run --recover first")
    directory.mkdir()
    journal = {"root": str(root.resolve()), "phase": "preparing", "files": []}
    replace = replace or os.replace
    try:
        save_journal(directory, journal)
        for relative in sorted(changed, key=lambda p: (p == "manifest.json", p)):
            target = safe_path(root, relative)
            require(not target.is_symlink(), "Symlinked output: " + relative)
            old = target.read_bytes() if target.exists() else None
            staged = safe_path(directory / "new", relative)
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(plan[relative])
            if old is not None:
                backup = safe_path(directory / "old", relative)
                backup.parent.mkdir(parents=True, exist_ok=True)
                backup.write_bytes(old)
            journal["files"].append({"path": relative, "old_sha256": sha256(old) if old is not None else None, "new_sha256": sha256(plan[relative])})
        journal["phase"] = "prepared"
        save_journal(directory, journal)
    except BaseException:
        shutil.rmtree(directory)
        raise
    try:
        journal["phase"] = "committing"
        save_journal(directory, journal)
        for item in journal["files"]:
            target = safe_path(root, item["path"])
            current = sha256(target.read_bytes()) if target.exists() else None
            require(current == item["old_sha256"], "File changed during import: " + item["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            replace(safe_path(directory / "new", item["path"]), target)
        journal["phase"] = "committed"
        save_journal(directory, journal)
    except BaseException:
        try:
            recover_transaction(root)
        except BaseException as recovery_error:
            print("Rollback could not complete; preserve " + str(directory) + " and run --recover: " + str(recovery_error), file=sys.stderr)
        raise
    shutil.rmtree(directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="Write generated books/catalogs/manifest after validating all inputs")
    mode.add_argument("--check", action="store_true", help="Check generated outputs without writing")
    mode.add_argument("--recover", action="store_true", help="Restore an interrupted write from its validated local backup")
    parser.add_argument("--offline", action="store_true", help="Require all pinned inputs already in the cache")
    parser.add_argument("--cache-dir", type=pathlib.Path, default=pathlib.Path.home() / ".cache/typebook-hf-readers")
    args = parser.parse_args()
    if args.recover:
        recover_transaction(ROOT)
        print(json.dumps({"status": "ok", "mode": "recover"}))
        return
    require(not transaction_directory(ROOT).exists(), "Interrupted import exists; run --recover first")
    cache = args.cache_dir.expanduser().resolve()
    require(not cache.is_relative_to(ROOT.resolve()), "Cache must be outside the resource repository")
    config = json.loads(CONFIG.read_text())
    validate_selection(config)
    dataset, upstream = config["dataset"], config["upstream"]
    hf_url = f'https://huggingface.co/datasets/{dataset["repository"]}/resolve/{dataset["revision"]}/{dataset["filename"]}'
    raw_base = f'https://raw.githubusercontent.com/{upstream["repository"]}/{upstream["revision"]}/'
    data = download(hf_url, dataset["sha256"], cache, args.offline, 40 * 1024 * 1024)
    require(len(data) == dataset["bytes"], "Dataset byte count differs")
    index = download(raw_base + upstream["index_path"], upstream["index_sha256"], cache, args.offline, 256 * 1024)
    originals = {book["filename"]: download(raw_base + "en/" + book["filename"], book["source_sha256"], cache, args.offline, 256 * 1024) for book in config["books"]}
    books, files = build_books(config, data, index, originals)
    plan = make_plan(ROOT, config, books, files)
    changed = [p for p, data in plan.items() if not (ROOT / p).is_file() or (ROOT / p).read_bytes() != data]
    if args.check:
        require(not changed, "Generated outputs differ: " + ", ".join(changed))
    if args.write:
        apply_plan(ROOT, plan, changed)
    print(json.dumps({"status": "ok", "mode": "write" if args.write else "check" if args.check else "dry-run", "readers": len(books), "chapters": sum(book["chapter_count"] for book in books), "words": sum(book["word_count"] for book in books), "changed_files": changed}, indent=2))


if __name__ == "__main__":
    def interrupted(signum, frame):
        raise KeyboardInterrupt("Import interrupted")
    signal.signal(signal.SIGTERM, interrupted)
    try:
        main()
    except (ValueError, KeyError, OSError, UnicodeError, csv.Error) as error:
        print("Import failed: " + str(error), file=sys.stderr)
        raise SystemExit(1)
