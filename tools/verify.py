#!/usr/bin/env python3
"""Verify a standalone TypeBook resource directory without network access."""
import hashlib
import json
import pathlib
import sys
from urllib.parse import unquote
from import_hf_readers import apply_title_translations
from rebuild_prompts import catalog_entry, load_prompts

ROOT = pathlib.Path(__file__).resolve().parent.parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_path(relative):
    require(isinstance(relative, str) and relative, "Missing relative path")
    decoded = unquote(relative)
    parts = pathlib.PurePosixPath(decoded)
    require(
        not parts.is_absolute() and not set(parts.parts) & {"..", "."}
        and "\\" not in decoded and ":" not in decoded and "\x00" not in decoded,
        "Unsafe path: " + relative,
    )
    path = ROOT / relative
    require(path.resolve().is_relative_to(ROOT), "Path escapes repository: " + relative)
    return path


def read_json(relative):
    return json.loads(safe_path(relative).read_text(encoding="utf-8-sig"))


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def verify_body(body):
    path = safe_path(body["path"])
    require(path.is_file(), "Missing body: " + body["path"])
    require(path.stat().st_size == body["bytes"], "Body size mismatch: " + body["path"])
    require(digest(path) == body["sha256"], "Body checksum mismatch: " + body["path"])


def model_dependencies(entrypoint):
    model = read_json(entrypoint)
    refs = model.get("FileReferences", {})
    paths = [refs[key] for key in ("Moc", "Physics", "Pose", "DisplayInfo", "UserData") if refs.get(key)]
    paths.extend(refs.get("Textures", []))
    paths.extend(item["File"] for item in refs.get("Expressions", []) if item.get("File"))
    for group in refs.get("Motions", {}).values():
        for item in group:
            paths.extend(item[key] for key in ("File", "Sound") if item.get(key))
    folder = pathlib.PurePosixPath(entrypoint).parent
    for path in paths:
        require(isinstance(path, str) and bool(path), "Invalid model dependency")
        full = (folder / path).as_posix()
        require(safe_path(full).is_file(), "Missing model dependency: " + full)
    return len(paths)


def main():
    manifest = read_json("manifest.json")
    require(manifest["schema_version"] == 1, "Unsupported manifest version")
    recorded = {}
    total_bytes = 0
    for item in manifest["files"]:
        relative = item["path"]
        require(relative not in recorded, "Duplicate manifest path: " + relative)
        path = safe_path(relative)
        require(path.is_file() and not path.is_symlink(), "Missing or symlinked file: " + relative)
        require(path.stat().st_size == item["bytes"], "Size mismatch: " + relative)
        require(digest(path) == item["sha256"], "Checksum mismatch: " + relative)
        recorded[relative] = item
        total_bytes += item["bytes"]
    actual = {
        file.relative_to(ROOT).as_posix() for file in ROOT.rglob("*")
        if file.is_file() and ".git" not in file.relative_to(ROOT).parts
        and "__pycache__" not in file.relative_to(ROOT).parts and file.name != ".DS_Store"
    } - {"manifest.json"}
    require(actual == set(recorded), "Manifest differs from directory: " + str(sorted(actual ^ set(recorded))))

    catalogs = {}
    for name, reference in manifest["catalogs"].items():
        require(reference["path"] in recorded, "Untracked catalog: " + name)
        catalogs[name] = read_json(reference["path"])
    for name in ("books", "dictionaries", "articles", "collections", "prompts", "live2d"):
        ids = [item["id"] for item in catalogs[name]]
        require(len(ids) == len(set(ids)), "Duplicate resource ID in " + name)

    chapter_count = 0
    translations = read_json("tools/book_titles.json")
    localized = apply_title_translations(catalogs["books"], translations, catalogs["books"])
    require(localized == catalogs["books"], "Catalog title translations differ from editorial source")
    for book in catalogs["books"]:
        require(book["chapter_count"] == len(book["chapters"]), "Chapter count mismatch: " + book["id"])
        verify_body(book["cover"])
        numbers = []
        for chapter in book["chapters"]:
            verify_body(chapter["body"])
            numbers.append(chapter["chapter_number"])
            require(safe_path(chapter["body"]["path"]).read_text(encoding="utf-8-sig").strip(), "Empty chapter")
        require(numbers == list(range(1, len(numbers) + 1)), "Non-sequential chapters: " + book["id"])
        chapter_count += len(numbers)
    dictionary_entries = 0
    for dictionary in catalogs["dictionaries"]:
        verify_body(dictionary["body"])
        words = read_json(dictionary["body"]["path"])
        require(isinstance(words, list) and len(words) == dictionary["word_count"], "Dictionary count mismatch: " + dictionary["id"])
        require(all(isinstance(word, dict) and isinstance(word.get("name"), str) and word["name"].strip() for word in words),
                "Invalid dictionary entry: " + dictionary["id"])
        dictionary_entries += len(words)
    for article in catalogs["articles"]:
        verify_body(article["body"])
    article_ids = {item["id"] for item in catalogs["articles"]}
    for collection in catalogs["collections"]:
        require(collection["item_count"] == len(collection["items"]), "Collection size mismatch")
        require(all(item in article_ids for item in collection["items"]), "Unknown collection article")
    prompt_sources = {p["id"]: p for p in load_prompts(ROOT)}
    require(set(prompt_sources) == {p["id"] for p in catalogs["prompts"]}, "Prompt source/catalog IDs differ")
    for prompt in catalogs["prompts"]:
        require(prompt == catalog_entry(prompt_sources[prompt["id"]]), "Prompt metadata differs: " + prompt["id"])
    require(catalogs["summary"]["prompts"] == len(prompt_sources), "Prompt summary count mismatch")
    require(manifest["counts"] == catalogs["summary"], "Manifest summary counts differ")
    dependencies = 0
    for model in catalogs["live2d"]:
        files = [item for name, item in recorded.items() if name.startswith(model["directory"])]
        require(len(files) == model["file_count"], "Model file count mismatch: " + model["id"])
        require(sum(item["bytes"] for item in files) == model["bytes"], "Model size mismatch: " + model["id"])
        dependencies += model_dependencies(model["entrypoint"])
        if model["thumbnail"]:
            require(safe_path(model["thumbnail"]).is_file(), "Missing model thumbnail")

    profile = read_json("profiles/default.json")
    require(len(profile["files"]) == len(set(profile["files"])), "Duplicate default-profile file")
    require(all(path in recorded for path in profile["files"]), "Unknown default-profile file")
    require(sum(recorded[path]["bytes"] for path in profile["files"]) == profile["payload_bytes"], "Default-profile size mismatch")
    default_paths = set(profile["files"])
    require(set(profile["prompts"]) == set(prompt_sources), "Default profile must include all prompts")
    require(all(p["path"] in default_paths for p in catalogs["prompts"]), "Default profile missing prompt payload")
    for name, key in (("books", "books"), ("dictionaries", "dictionaries"), ("articles", "articles"),
                      ("collections", "collections"), ("prompts", "prompts"), ("live2d", "models")):
        require(set(profile[key]) <= {item["id"] for item in catalogs[name]}, "Unknown default-profile ID: " + key)
    for model in catalogs["live2d"]:
        if model["id"] in profile["models"]:
            require(all(path in default_paths for path in recorded if path.startswith(model["directory"])),
                    "Default profile has incomplete model: " + model["id"])
    require(manifest["total_bytes"] == total_bytes, "Manifest total byte count differs")
    print(json.dumps({
        "status": "ok", "files_verified": len(recorded), "bytes_verified": total_bytes,
        "books": len(catalogs["books"]), "chapters": chapter_count,
        "books_with_localized_titles": len(localized), "title_locales": ["en", "zh-CN", "ja"],
        "dictionaries": len(catalogs["dictionaries"]), "dictionary_entries": dictionary_entries,
        "articles": len(catalogs["articles"]), "collections": len(catalogs["collections"]),
        "prompts": len(catalogs["prompts"]),
        "prompts_with_localized_titles": len(prompt_sources),
        "prompts_with_localized_bodies": len(prompt_sources),
        "prompt_body_locales": ["en", "zh-CN", "ja"],
        "prompt_categories": {category: sum(p["category"] == category for p in prompt_sources.values())
                              for category in ("english-learning", "typing-practice", "image-generation")},
        "models": len(catalogs["live2d"]),
        "model_dependencies_verified": dependencies, "default_profile_bytes": profile["payload_bytes"]
    }, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (KeyError, ValueError, OSError, json.JSONDecodeError) as error:
        print("Verification failed: " + str(error), file=sys.stderr)
        raise SystemExit(1)
