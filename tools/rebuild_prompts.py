#!/usr/bin/env python3
"""Validate prompt sources; deterministically rebuild their catalog and manifest.

No network or third-party packages. Default: dry run. --render prints a resolved
prompt locally; it never contacts a model or submits content to a provider.
"""
import argparse
import json
import pathlib
import re
import sys
import unicodedata
from collections import Counter
from import_hf_readers import (ROOT, apply_plan, json_bytes, recover_transaction,
                               require, resource_files, safe_path, sha256,
                               transaction_directory)

LOCALES = {"en", "zh-CN", "ja"}
LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2"}
CATEGORIES = {"english-learning", "typing-practice", "image-generation"}
TOKEN = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")
ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
SUPPORT_FILES = {"tools/rebuild_prompts.py", "tests/test_prompts.py", "docs/prompts.md"}


def clean_text(value, multiline=False):
    return (isinstance(value, str) and bool(value) and value == value.strip()
            and not any(unicodedata.category(c).startswith("C")
                        and not (multiline and c == "\n") for c in value))


def validate_prompt(prompt):
    require(isinstance(prompt, dict), "Prompt must be an object")
    pid = prompt.get("id")
    require(isinstance(pid, str) and ID.fullmatch(pid), "Invalid prompt ID")
    for field in ("name", "description"):
        require(clean_text(prompt.get(field)), f"Invalid {field}: {pid}")
    require(prompt.get("source_type") == "official", "Invalid prompt source: " + pid)
    require(prompt.get("display_type") in {"chat", "reading"}, "Invalid display_type: " + pid)
    titles = prompt.get("title_i18n")
    require(isinstance(titles, dict) and set(titles) == LOCALES, "Invalid title locales: " + pid)
    require(all(clean_text(v) for v in titles.values()), "Invalid localized title: " + pid)
    require(titles["en"] == prompt["name"], "English title differs from name: " + pid)
    require(prompt.get("category") in CATEGORIES, "Invalid category: " + pid)
    require(prompt.get("output_type") in {"text", "image"}, "Invalid output_type: " + pid)
    require((prompt["category"] == "image-generation") == (prompt["output_type"] == "image"),
            "Image category/output mismatch: " + pid)
    require(prompt["output_type"] != "image" or prompt["display_type"] == "chat", "Image cannot be reading text: " + pid)
    require(prompt.get("prompt_role") in {"system", "user"}, "Invalid prompt_role: " + pid)
    if "legacy_id" in prompt:
        require(type(prompt["legacy_id"]) is int and prompt["legacy_id"] < 0, "Invalid legacy_id: " + pid)
    for field in ("tags", "cefr_levels"):
        values = prompt.get(field)
        require(isinstance(values, list) and values and all(clean_text(v) for v in values), "Invalid " + field + ": " + pid)
        require(len(values) == len(set(values)), "Duplicate " + field + ": " + pid)
    require(set(prompt["cefr_levels"]) <= LEVELS, "Invalid CEFR level: " + pid)
    body = prompt.get("prompt")
    require(clean_text(body, multiline=True), "Empty or invalid prompt body: " + pid)
    bodies = prompt.get("prompt_i18n")
    require(isinstance(bodies, dict) and set(bodies) == LOCALES, "Invalid prompt locales: " + pid)
    require(all(clean_text(v, multiline=True) for v in bodies.values()), "Invalid localized prompt: " + pid)
    require(bodies["en"] == body, "English prompt differs from prompt: " + pid)
    variables = prompt.get("variables")
    require(isinstance(variables, list), "Invalid variables: " + pid)
    names = []
    for variable in variables:
        require(isinstance(variable, dict) and set(variable) == {"name", "default", "description"}, "Invalid variable fields: " + pid)
        name = variable["name"]
        require(isinstance(name, str) and re.fullmatch(r"[a-z][a-z0-9_]*", name), "Invalid variable name: " + pid)
        require(clean_text(variable["default"]) and clean_text(variable["description"]), "Invalid variable value: " + pid)
        require("{{" not in variable["default"] and "}}" not in variable["default"], "Nested variable default: " + pid)
        names.append(name)
    require(len(names) == len(set(names)), "Duplicate variable: " + pid)
    require(set(TOKEN.findall(body)) == set(names), "Placeholder/variable mismatch: " + pid)
    for locale, localized in bodies.items():
        require(Counter(TOKEN.findall(localized)) == Counter(TOKEN.findall(body)),
                "Localized placeholder mismatch: " + pid + " / " + locale)
        remainder = TOKEN.sub("", localized)
        require("{{" not in remainder and "}}" not in remainder,
                "Malformed placeholder: " + pid + " / " + locale)


def render_prompt(prompt, values=None, locale="en"):
    """One literal substitution pass; values are data, never executable code."""
    validate_prompt(prompt)
    require(isinstance(locale, str) and bool(locale), "Locale must be a nonempty string")
    require(values is None or isinstance(values, dict), "Variable overrides must be an object")
    values = {} if values is None else values
    resolved = {item["name"]: item["default"] for item in prompt["variables"]}
    require(set(values) <= set(resolved), "Unknown variable overrides")
    require(all(clean_text(v, multiline=True) for v in values.values()), "Invalid variable override")
    require(all("{{" not in v and "}}" not in v for v in values.values()), "Nested placeholder in override")
    resolved.update(values)
    body = prompt["prompt_i18n"].get(locale, prompt["prompt"])
    return TOKEN.sub(lambda match: resolved[match.group(1)], body)


def load_prompts(root):
    prompts = []
    for path in sorted((root / "prompts").glob("*.json")):
        require(not path.is_symlink(), "Symlinked prompt: " + path.name)
        prompt = json.loads(path.read_text(encoding="utf-8"))
        validate_prompt(prompt)
        require(path.name == prompt["id"] + ".json", "Prompt filename/ID mismatch: " + path.name)
        prompts.append(prompt)
    require(prompts, "No prompt sources")
    ids = [p["id"] for p in prompts]
    require(len(ids) == len(set(ids)), "Duplicate prompt ID")
    legacy_ids = [p["legacy_id"] for p in prompts if "legacy_id" in p]
    require(len(legacy_ids) == len(set(legacy_ids)), "Duplicate legacy prompt ID")
    return prompts


def catalog_entry(prompt):
    return {**{key: value for key, value in prompt.items() if key not in {"prompt", "prompt_i18n"}},
            "path": "prompts/" + prompt["id"] + ".json"}


def make_plan(root):
    prompts = {p["id"]: p for p in load_prompts(root)}
    old_catalog = json.loads((root / "catalogs/prompts.json").read_text())
    old_ids = [item["id"] for item in old_catalog]
    require(len(old_ids) == len(set(old_ids)), "Duplicate old catalog ID")
    require(set(old_ids) <= set(prompts), "Removing existing prompts is not supported")
    ordered = old_ids + sorted(set(prompts) - set(old_ids))
    catalog = [catalog_entry(prompts[pid]) for pid in ordered]
    outputs = {"catalogs/prompts.json": json_bytes(catalog)}
    summary = json.loads((root / "catalogs/summary.json").read_text())
    summary["prompts"] = len(catalog)
    outputs["catalogs/summary.json"] = json_bytes(summary)
    profile = json.loads((root / "profiles/default.json").read_text())
    profile["prompts"] = list(dict.fromkeys(profile["prompts"] + ordered))
    require(set(profile["prompts"]) == set(prompts), "Unknown default-profile prompt")
    profile["files"] = sorted(set(profile["files"]) | {item["path"] for item in catalog})
    profile["payload_bytes"] = sum(len(outputs[p]) if p in outputs else safe_path(root, p).stat().st_size
                                   for p in profile["files"])
    outputs["profiles/default.json"] = json_bytes(profile)
    manifest = json.loads((root / "manifest.json").read_text())
    recorded = {item["path"]: item for item in manifest["files"]}
    actual = {p.relative_to(root).as_posix() for p in resource_files(root)}
    allowed = set(recorded) | set(outputs) | SUPPORT_FILES | {item["path"] for item in catalog}
    require(not actual - allowed, "Unexpected local files; not adding to manifest: " + ", ".join(sorted(actual - allowed)))
    require(not set(recorded) - actual, "Removing recorded files is not supported")
    require(not any(p.endswith(".tmp") for p in actual), "Temporary file found; refusing manifest update")
    files = []
    for relative in sorted(actual | set(outputs)):
        path = safe_path(root, relative)
        require(not path.is_symlink(), "Symlinked resource: " + relative)
        data = outputs[relative] if relative in outputs else path.read_bytes()
        entry = dict(recorded.get(relative, {}))
        entry.update(path=relative, bytes=len(data), sha256=sha256(data))
        entry.setdefault("content_type", {".json": "application/json", ".md": "text/markdown", ".py": "text/x-python"}.get(path.suffix, "application/octet-stream"))
        entry.setdefault("category", "prompt" if relative.startswith("prompts/") else "documentation" if relative.startswith("docs/") else "tooling")
        if relative.startswith("prompts/"):
            if "source" not in entry:
                entry["source"] = {"kind": "original-typebook-prompt"}
            elif entry["source"].get("kind") == "frontend-builtin":
                entry["source"] = {**entry["source"], "metadata_note": "Additive display and usage metadata authored in this resource repository; original prompt fields preserved."}
        files.append(entry)
    manifest.update(counts=summary, files=files, total_bytes=sum(p["bytes"] for p in files))
    # This descriptive revision is supplied only on an intentional catalog update.
    # Later book-only imports preserve it when their generated book data is unchanged.
    if outputs["catalogs/prompts.json"] != (root / "catalogs/prompts.json").read_bytes():
        manifest["revision"] = "2026-11-07-multilingual-storybook-prompts"
    outputs["manifest.json"] = json_bytes(manifest)
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--recover", action="store_true")
    modes.add_argument("--render", metavar="PROMPT_ID")
    parser.add_argument("--locale", help="Instruction locale for --render: en, zh-CN, ja; other locales fall back to English")
    parser.add_argument("--values", help='JSON object, e.g. {"word":"pear"}; --render only')
    args = parser.parse_args()
    require(args.values is None or args.render, "--values requires --render")
    require(args.locale is None or args.render, "--locale requires --render")
    if args.recover:
        recover_transaction(ROOT)
        print(json.dumps({"status": "ok", "mode": "recover"}))
        return
    require(not transaction_directory(ROOT).exists(), "Interrupted resource import exists; run --recover first")
    if args.render:
        prompts = {p["id"]: p for p in load_prompts(ROOT)}
        require(args.render in prompts, "Unknown prompt ID")
        print(render_prompt(prompts[args.render], json.loads(args.values) if args.values else None, args.locale or "en"))
        return
    plan = make_plan(ROOT)
    changed = [p for p, data in plan.items() if not (ROOT / p).is_file() or (ROOT / p).read_bytes() != data]
    if args.check:
        require(not changed, "Generated outputs differ: " + ", ".join(changed))
    if args.write:
        apply_plan(ROOT, plan, changed)
    print(json.dumps({"status": "ok", "mode": "write" if args.write else "check" if args.check else "dry-run",
                      "prompts": len(load_prompts(ROOT)), "changed_files": changed}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, UnicodeError, TypeError) as error:
        print("Prompt build failed: " + str(error), file=sys.stderr)
        raise SystemExit(1)
