"""Sync skill.md front matter from skill.yaml for 3.4 domains."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1] / "skills"
DOMAINS = {"neural", "evolutionary", "hybrid", "scientific"}


def body_after_fm(text: str) -> str:
    text = text.lstrip("\ufeff")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].lstrip("\n")
    return text


def main() -> None:
    for p in ROOT.rglob("skill.yaml"):
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if data.get("domain") not in DOMAINS:
            continue
        md_path = p.parent / "skill.md"
        old = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
        body = body_after_fm(old)
        if not body.strip():
            body = (
                f"# {data.get('title', data['id'])}\n\n"
                "Requires optional extras as documented in skill.yaml.\n"
            )
        fm = {
            "id": data["id"],
            "version": data.get("version", "0.1.0"),
            "status": data.get("status", "experimental"),
            "domain": data.get("domain"),
            "title": data.get("title", data["id"]),
        }
        fm_yaml = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
        md_path.write_text(f"---\n{fm_yaml}\n---\n\n{body}", encoding="utf-8")
        print("fixed", data["id"])


if __name__ == "__main__":
    main()
