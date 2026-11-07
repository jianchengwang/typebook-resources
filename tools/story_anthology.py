"""Build one multi-story book while preserving standalone records and payloads.

Invoked by import_hf_readers.py; no copying or rewriting of story text is needed.
"""
import copy
import json
import pathlib
from collections import Counter
from import_hf_readers import body_ref, json_bytes, require, safe_path, sha256

SUPPORT_FILES = {"tools/story_anthology.py", "tools/story_anthology.json",
                 "tests/test_story_anthology.py", "docs/childrens-short-stories.md"}
CREDITS_URL = "https://github.com/jianchengwang/typebook-resources/blob/main/books/childrens-short-stories/LICENSE.md"


def read_config(root, config):
    path = config.get("anthology_path")
    if not path:
        return None
    value = json.loads(safe_path(root, path).read_text())
    require(value["schema_version"] == 1, "Unsupported anthology schema")
    require(value["id"] == f'book:{value["legacy_id"]}', "Invalid anthology ID")
    require(value["reader_import_id"] == config["import_id"], "Wrong anthology source")
    require(value["order"] == "word_count_then_legacy_id", "Unsupported story order")
    require(type(value["chapter_id_offset"]) is int and value["chapter_id_offset"] > 0,
            "Invalid anthology chapter offset")
    for key in ("archive_path", "mapping_path"):
        safe_path(root, value[key])
    safe_path(root, "books/" + value["slug"] + "/source.json")
    return value


def preserved_books(root, books, config):
    """Combine public and compatibility records without changing either."""
    if not config:
        return books
    archive = safe_path(root, config["archive_path"])
    archived = json.loads(archive.read_text()) if archive.exists() else []
    require(isinstance(archived, list), "Invalid standalone-reader archive")
    require(all(book.get("source", {}).get("import_id") == config["reader_import_id"]
                for book in archived), "Archive contains unrelated books")
    result = books + archived
    require(len({b["id"] for b in result}) == len(result), "Duplicate public/archive book ID")
    return result


def build(root, config, books, titles, outputs):
    """Return public books, generated files and manifest compatibility metadata."""
    sources = [b for b in books if b.get("source", {}).get("import_id") == config["reader_import_id"]]
    others = [b for b in books if b not in sources]
    require(sources, "No short stories for anthology")
    require(config["id"] not in {b["id"] for b in books}, "Anthology book ID collision")
    require(all(b["chapter_count"] == len(b["chapters"]) == 1 for b in sources),
            "Anthology can include only complete single-chapter stories")
    require(all(b["license_status"] == "verified-cc-by" for b in sources), "Unverified story license")
    title = titles[config["id"]]
    folder = "books/" + config["slug"]
    chapters, mappings, credit_sections, compact_credits, seen_bodies = [], [], [], [], set()
    existing_chapter_ids = {c["id"] for b in books for c in b["chapters"]}
    total_bytes = 0
    def data_at(path):
        return outputs[path] if path in outputs else safe_path(root, path).read_bytes()
    for number, book in enumerate(sorted(sources, key=lambda b: (b["word_count"], b["legacy_id"])), 1):
        original = book["chapters"][0]
        body = original["body"]
        data = data_at(body["path"])
        require(body == body_ref(body["path"], data), "Story body checksum mismatch: " + book["id"])
        require(body["sha256"] not in seen_bodies, "Duplicate anthology story text")
        seen_bodies.add(body["sha256"])
        require(len(data.decode("utf-8").split()) == book["word_count"], "Story word count mismatch")
        require(book["license"]["id"] in ("CC-BY-3.0", "CC-BY-4.0"), "Unsupported story license")
        require(original["license_label"] == book["license"]["id"] and
                original["license_url"] == book["license"]["url"], "Chapter license differs")
        require(all(original.get(k) for k in ("source_url", "attribution", "adaptation_note")),
                "Missing story attribution")
        source = json.loads(data_at(book["source"]["path"]))
        require(source["license"] == book["license"] and source["author"] == book["author"],
                "Story provenance differs")
        source_folder = str(pathlib.PurePosixPath(book["source"]["path"]).parent)
        require(source["upstream_sha256"] == sha256(data_at(source_folder + "/original.md")),
                "Original story checksum mismatch: " + book["id"])
        chapter_id = original["legacy_id"] + config["chapter_id_offset"]
        require(f"chapter:{chapter_id}" not in existing_chapter_ids, "Anthology chapter ID collision")
        chapter = copy.deepcopy(original)
        chapter.update(id=f"chapter:{chapter_id}", legacy_id=chapter_id, book_id=config["legacy_id"],
                       chapter_number=number, title_i18n=book["title_i18n"], author=book["author"],
                       source_book_id=book["id"], source_chapter_id=original["id"],
                       license=book["license"], source=book["source"], practice=source["practice"])
        chapters.append(chapter)
        mappings.append({"source_book_id": book["id"], "source_chapter_id": original["id"],
                         "book_id": config["id"], "chapter_id": chapter["id"],
                         "chapter_number": number, "body": body})
        license_path = source_folder + "/LICENSE.md"
        credit_sections.append(f'## {number}. {book["title"]}\n\n'
                               f'Original IDs: `{book["id"]}`, `{original["id"]}`. '
                               f'Anthology chapter: `{chapter["id"]}`.\n\n'
                               + data_at(license_path).decode().removeprefix("# " + book["title"] + "\n").lstrip())
        # Local consumers currently retain the book description, not chapter credit fields.
        # Keep all contributor/publisher notices here as well, without touching practice text.
        compact_credits.append(f'{number}. {book["title"]} | {original["attribution"]} '
                               f'{original["license_label"]}: {original["license_url"]}')
        total_bytes += len(data)
    cover = (f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="640" viewBox="0 0 480 640">\n'
             '<rect width="480" height="640" fill="#f7f0db"/><rect x="20" y="20" width="440" height="600" rx="12" fill="none" stroke="#296b59" stroke-width="2"/>\n'
             '<circle cx="373" cy="140" r="49" fill="#e6aa50"/><path d="M62 411 Q145 369 240 413 Q335 369 418 411 L418 521 Q335 479 240 523 Q145 479 62 521Z" fill="#296b59"/>\n'
             '<path d="M240 413V523" stroke="#f7f0db" stroke-width="3"/>\n'
             '<g fill="#204d40" font-family="sans-serif"><text x="52" y="85" font-size="15" letter-spacing="2">ENGLISH STORY COLLECTION</text>\n'
             '<text x="52" y="204" font-size="43" font-weight="700">Children\'s</text><text x="52" y="257" font-size="43" font-weight="700">Short Stories</text>\n'
             f'<text x="52" y="311" font-size="21">{len(chapters)} stories · One story per chapter</text>'
             '<text x="52" y="579" font-size="16">READ · EXPLORE · PRACTISE</text></g></svg>\n').encode()
    credits = ("# Children's Short Stories: per-story credits\n\n"
               "This is a collection of separately licensed works, not a new blanket license. "
               "Each story retains its original CC BY 3.0 or CC BY 4.0 license, contributor credits, "
               "source links and adaptation notice below. The anthology reuses the existing chapter "
               "bytes without changes. No illustrations from the sources are included. "
               "The new typographic cover and arrangement are TypeBook editorial work.\n\n"
               + "\n".join(credit_sections)).encode()
    description = (f'{len(chapters)} complete English children\'s stories, one story per chapter, '
                   f'ordered from shorter to longer ({min(b["word_count"] for b in sources)}–{max(b["word_count"] for b in sources)} words each). Original texts and credits '
                   'are preserved. Individual stories are CC BY 3.0 or CC BY 4.0; no blanket license. '
                   'Read each author, source, license and modification notice at: ' + CREDITS_URL
                   + '\n\nPer-story credits (retained by legacy local importers):\n' + '\n\n'.join(compact_credits))
    book = {"id": config["id"], "legacy_id": config["legacy_id"], "title": title["en"],
            "title_i18n": title, "author": "Various authors (see per-story credits)",
            "description": description,
            "description_i18n": {"en": description,
                "zh-CN": f'{len(chapters)}篇完整英文儿童短故事，每篇一章，按篇幅从短到长排列。各篇作者、来源、CC BY 3.0/4.0许可及改编说明：' + CREDITS_URL,
                "ja": f'{len(chapters)}編の英語の子ども向け短編を、1編1章で短い順に収録。各作品の著者、出典、CC BY 3.0/4.0ライセンスと変更内容：' + CREDITS_URL},
            "tags": json.dumps(["english-learning", "childrens-stories", "anthology", "typing-practice"]),
            "word_count": sum(b["word_count"] for b in sources), "chapter_count": len(chapters),
            "revision": 1, "license_status": "verified-cc-by-per-chapter",
            "licenses": [{"id": "CC-BY-3.0", "url": "https://creativecommons.org/licenses/by/3.0/"},
                         {"id": "CC-BY-4.0", "url": "https://creativecommons.org/licenses/by/4.0/"}],
            "attribution_path": folder + "/LICENSE.md",
            "source": {"import_id": config["import_id"], "path": folder + "/source.json"},
            "cover": body_ref(folder + "/cover.svg", cover), "chapters": chapters}
    provenance = {"schema_version": 1, "import_id": config["import_id"], "title_i18n": title,
                  "reader_import_id": config["reader_import_id"], "archive_path": config["archive_path"],
                  "mapping_path": config["mapping_path"], "ordering": config["order"],
                  "story_count": len(chapters), "word_count": book["word_count"],
                  "license_counts": dict(sorted(Counter(b["license"]["id"] for b in sources).items())),
                  "reused_body_bytes": total_bytes, "new_body_bytes": 0,
                  "changes": "Arrangement only. Existing normalized English chapter bytes are reused without alteration. Original source and normalization notices remain per story."}
    files = {config["archive_path"]: json_bytes(sources),
             config["mapping_path"]: json_bytes({"schema_version": 1, "target_book_id": config["id"],
                 "archive_path": config["archive_path"], "policy": "opt-in; preserve old IDs, progress and local copies", "items": mappings}),
             folder + "/cover.svg": cover, folder + "/LICENSE.md": credits,
             folder + "/source.json": json_bytes(provenance)}
    return others + [book], files
