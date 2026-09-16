#!/usr/bin/env python3
"""Prompt defense audit over skills and repository instructions for APGR."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

UNSAFE_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*:\s*you\s+are\s+now", re.IGNORECASE),
    re.compile(r"<\s*script(?:\s+type|\s+src|\s*>)", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"data\s*:\s*text/html", re.IGNORECASE),
]

UNICODE_DANGEROUS = [
    "\u202e",  # Right-to-Left Override
    "\u202d",  # Left-to-Right Override
    "\u200b",  # Zero-Width Space
    "\u200c",  # Zero-Width Non-Joiner
    "\u200d",  # Zero-Width Joiner
    "\ufeff",  # Byte Order Mark inside text
]


def audit_prompts() -> dict:
    skills_dir = ROOT / "skills"
    skill_files = sorted(skills_dir.glob("**/SKILL.md")) if skills_dir.is_dir() else []
    missing = [] if skill_files else ["skills/SKILL.md inventory"]
    targets = [ROOT / "AGENTS.md", *skill_files]

    embedded_payloads = []
    unicode_issues = []
    total_files = 0

    for sf in targets:
        rel_path = str(sf.relative_to(ROOT))
        try:
            if sf.is_symlink() or not sf.is_file():
                raise OSError("instruction input is not a direct regular file")
            content = sf.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            missing.append(rel_path)
            continue
        total_files += 1

        for pat in UNSAFE_PATTERNS:
            m = pat.search(content)
            if m:
                embedded_payloads.append({
                    "file": rel_path,
                    "pattern": pat.pattern,
                    "match": m.group(0),
                })

        for u in UNICODE_DANGEROUS:
            if u in content:
                unicode_issues.append({
                    "file": rel_path,
                    "char_hex": hex(ord(u)),
                })

    score = 100 - (len(embedded_payloads) * 10) - (len(unicode_issues) * 5)
    score = max(0, min(100, score))

    return {
        "version": 1,
        "profile": "prompt-defense-audit",
        "total_files_audited": total_files,
        "score": score,
        "missing": missing,
        "embedded_payloads": embedded_payloads,
        "unicode_issues": unicode_issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", default=True)
    parser.parse_args(argv)

    report = audit_prompts()
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["missing"]:
        return 2
    return 0 if report["score"] >= 80 and not report["embedded_payloads"] and not report["unicode_issues"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
