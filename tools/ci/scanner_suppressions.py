#!/usr/bin/env python3
"""Scanner suppression inventory and drift control for APGR."""

from __future__ import annotations

import argparse
import ast
from datetime import date
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tokenize

ROOT = Path(__file__).resolve().parents[2]

SUPPRESSION_PATTERNS = {
    "noqa": re.compile(r"#\s*noqa(?::\s*([A-Za-z0-9*,\s]+))?", re.IGNORECASE),
    "type_ignore": re.compile(r"#\s*type:\s*ignore(?:\[([a-zA-Z0-9,\s_-]+)\])?"),
    "nosemgrep": re.compile(r"(?:#|//)\s*nosemgrep(?::\s*([A-Za-z0-9_.-]+))?"),
    "nolint_go": re.compile(r"//\s*nolint(?::\s*([a-zA-Z0-9,\s_-]+))?"),
    "hadolint_ignore": re.compile(r"#\s*hadolint\s+ignore=([A-Za-z0-9,]+)"),
    "actionlint_disable": re.compile(r"#\s*actionlint-disable(?:-line|-next-line)?(?:\s+([a-zA-Z0-9_-]+))?"),
    "zizmor_ignore": re.compile(r"#\s*zizmor:ignore\[([a-zA-Z0-9_-]+)\]"),
}

KNOWN_SUPPRESSIONS_FILE = Path(__file__).resolve().parent / "scanner_suppressions_known.json"
SCHEMA_V2 = "apg-scanner-suppression-inventory-v3"
APPROVAL_SCHEMA = "apg-scanner-suppression-approvals-v1"


def normalize_rule(rule: str | None) -> str:
    """Canonical sorted comma-separated normalization for rule strings."""
    if not rule or rule.strip() == "" or rule.strip() == "*":
        return "*"
    parts = [p.strip() for p in re.split(r"[\s,]+", rule.strip()) if p.strip()]
    if not parts:
        return "*"
    return ", ".join(sorted(set(parts)))


def suppression_identity(s: dict) -> tuple[str, str, str, str]:
    """Identity tuple: (path, kind, normalized_rule, context). Line is diagnostic."""
    return (
        s["path"],
        s["kind"],
        normalize_rule(s.get("rule")),
        s.get("context", ""),
    )


def scan_python_text(text: str, lines: list[str], rel_path: str) -> list[dict]:
    """Extract suppressions from Python source text using Python tokenize."""
    try:
        tokens = list(tokenize.tokenize(io.BytesIO(text.encode("utf-8")).readline))
        tree = ast.parse(text)
    except (tokenize.TokenError, IndentationError, SyntaxError) as error:
        raise ValueError("tracked suppression input unavailable") from error

    suppressions = []
    for tok in tokens:
        if tok.type != tokenize.COMMENT:
            continue
        comment_text = tok.string
        if not any(SUPPRESSION_PATTERNS[kind].search(comment_text)
                   for kind in ("noqa", "type_ignore", "nosemgrep")):
            continue
        lineno = tok.start[0]
        col_offset = tok.start[1]
        phys_line = tok.line

        prefix = phys_line[:col_offset].strip()
        if prefix:
            context = prefix
        else:
            context = ""
            for following in lines[lineno:]:
                s = following.strip()
                if s and not s.startswith("#"):
                    context = s
                    break
        # Bind the full owning statement, including multiline imports, and
        # enclosing function/class names. Source line movement is immaterial.
        statements = [node for node in ast.walk(tree) if isinstance(node, ast.stmt)
                      and node.lineno <= lineno <= node.end_lineno]
        if not statements:
            statements = [node for node in ast.walk(tree) if isinstance(node, ast.stmt)
                          and node.lineno > lineno]
            statements.sort(key=lambda node: node.lineno)
            statements = statements[:1]
        if statements:
            node = min(statements, key=lambda item: item.end_lineno - item.lineno)
            scopes = [(item.lineno, item.name) for item in ast.walk(tree)
                      if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                      and item.lineno <= node.lineno <= item.end_lineno and item is not node]
            # Scope line numbers are diagnostics too, so only names enter identity.
            context = json.dumps([[name for _, name in sorted(scopes)], ast.dump(node, include_attributes=False)])
        context = "sha256:" + hashlib.sha256(context.encode()).hexdigest()

        for kind in ("noqa", "type_ignore", "nosemgrep"):
            m = SUPPRESSION_PATTERNS[kind].search(comment_text)
            if m:
                raw_rule = m.group(1).strip() if m.group(1) else "*"
                suppressions.append({
                    "path": rel_path,
                    "line": lineno,
                    "kind": kind,
                    "rule": normalize_rule(raw_rule),
                    "context": context,
                })
    return suppressions


def scan_go_lines(lines: list[str], rel_path: str) -> list[dict]:
    """Extract suppressions from Go files, distinguishing string literals from comments."""
    suppressions = []
    in_raw_string = False
    for idx, line in enumerate(lines, start=1):
        in_double_quote = False
        escape = False
        comment_start = -1
        i = 0
        while i < len(line):
            ch = line[i]
            if in_raw_string:
                if ch == "`":
                    in_raw_string = False
            elif in_double_quote:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_double_quote = False
            else:
                if ch == "`":
                    in_raw_string = True
                elif ch == '"':
                    in_double_quote = True
                elif ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                    comment_start = i
                    break
            i += 1

        if comment_start != -1:
            comment_text = line[comment_start:]
            prefix = line[:comment_start].strip()
            if prefix:
                context = prefix
            else:
                context = ""
                for following in lines[idx:]:
                    s = following.strip()
                    if s and not s.startswith("//") and not s.startswith("/*"):
                        context = s
                        break
            context = context[:200]
            for kind in ("nolint_go", "nosemgrep"):
                m = SUPPRESSION_PATTERNS[kind].search(comment_text)
                if m:
                    raw_rule = m.group(1).strip() if m.group(1) else "*"
                    suppressions.append({
                        "path": rel_path,
                        "line": idx,
                        "kind": kind,
                        "rule": normalize_rule(raw_rule),
                        "context": context,
                    })
    return suppressions


def scan_hash_comment_lines(lines: list[str], rel_path: str, kinds: tuple[str, ...]) -> list[dict]:
    """Extract suppressions from hash-commented formats (YAML, Dockerfile, shell)."""
    suppressions = []
    for idx, line in enumerate(lines, start=1):
        in_quote = None
        escape = False
        comment_start = -1
        for i, ch in enumerate(line):
            if in_quote:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == in_quote:
                    in_quote = None
            else:
                if ch in ('"', "'"):
                    in_quote = ch
                elif ch == "#":
                    comment_start = i
                    break

        if comment_start != -1:
            comment_text = line[comment_start:]
            prefix = line[:comment_start].strip()
            if prefix:
                context = prefix
            else:
                context = ""
                for following in lines[idx:]:
                    s = following.strip()
                    if s and not s.startswith("#"):
                        context = s
                        break
            context = context[:200]
            for kind in kinds:
                m = SUPPRESSION_PATTERNS[kind].search(comment_text)
                if m:
                    raw_rule = m.group(1).strip() if m.group(1) else "*"
                    suppressions.append({
                        "path": rel_path,
                        "line": idx,
                        "kind": kind,
                        "rule": normalize_rule(raw_rule),
                        "context": context,
                    })
    return suppressions


def scan_file(p: Path, rel_path: str) -> list[dict]:
    """Bounded, honest scan of an individual tracked file."""
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeError) as error:
        raise ValueError("tracked suppression input unavailable") from error

    lines = text.splitlines()
    first_line = lines[0] if lines else ""

    is_py = p.suffix == ".py" or (first_line.startswith("#!") and "python" in first_line)
    if is_py:
        return scan_python_text(text, lines, rel_path)
    if p.suffix == ".go":
        return scan_go_lines(lines, rel_path)
    if p.suffix in (".yml", ".yaml"):
        return scan_hash_comment_lines(lines, rel_path, ("actionlint_disable", "zizmor_ignore", "nosemgrep"))
    if p.name == "Dockerfile" or p.name.startswith("Dockerfile.") or p.suffix == ".dockerfile":
        return scan_hash_comment_lines(lines, rel_path, ("hadolint_ignore", "nosemgrep"))
    if p.suffix in (".sh", ".bash") or (first_line.startswith("#!") and any(sh in first_line for sh in ("sh", "bash", "zsh"))):
        return scan_hash_comment_lines(lines, rel_path, ("nosemgrep",))
    return []


def scan_suppressions(root: Path | None = None) -> list[dict]:
    """Scan tracked public source tree for active suppression directives."""
    if root is None:
        root = ROOT
    suppressions = []
    try:
        res = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        files = [f for f in res.stdout.splitlines() if f]
    except (OSError, subprocess.SubprocessError, UnicodeError) as error:
        raise ValueError("tracked public source inventory unavailable") from error

    for rel_path in sorted(files):
        # Public CI must not read or publish private evidence and oracle paths.
        if rel_path.startswith("private/") or ".git" in Path(rel_path).parts:
            continue
        p = root / rel_path
        if p.is_symlink():
            if rel_path.startswith(".agents/skills/"):
                continue
            raise ValueError("tracked suppression input is a symlink")
        if not p.is_file():
            raise ValueError("tracked suppression input missing")
        suppressions.extend(scan_file(p, rel_path))
    return suppressions


def is_entry_approved(entry: dict) -> bool:
    """Validate review decision: accepted, concrete owner, reason, future expiry."""
    norm_rule = normalize_rule(entry.get("rule"))
    if "*" in norm_rule:
        return False
    if not entry.get("context") or not isinstance(entry.get("review"), str) or not entry["review"].strip():
        return False
    if entry["review"].lower().strip() in {"pending", "unreviewed", "pre_final", "tbd"}:
        return False
    owner = entry.get("owner")
    if not owner or not isinstance(owner, str) or not owner.strip():
        return False
    reason = entry.get("reason")
    if not reason or not isinstance(reason, str) or not reason.strip():
        return False
    if entry.get("disposition") != "accepted":
        return False
    expiry_val = entry.get("expiry")
    if not expiry_val or not isinstance(expiry_val, str):
        return False
    try:
        exp_date = date.fromisoformat(expiry_val)
        if exp_date < date.today():
            return False
    except (ValueError, TypeError):
        return False
    return True


def build_inventory(known_file: Path | None = None, root: Path | None = None) -> dict:
    """Build suppression drift inventory against known reviewed suppressions."""
    if known_file is None:
        known_file = KNOWN_SUPPRESSIONS_FILE
    if root is None:
        root = ROOT

    current = scan_suppressions(root=root)

    if not known_file.is_file():
        raise OSError(f"known suppressions file not found: {known_file}")

    try:
        raw_text = known_file.read_text(encoding="utf-8")
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate suppression JSON key")
                result[key] = value
            return result
        known_doc = json.loads(raw_text, object_pairs_hook=unique)
    except (json.JSONDecodeError, UnicodeError, OSError) as error:
        raise ValueError("invalid suppression review inventory JSON") from error

    if not isinstance(known_doc, dict) or "suppressions" not in known_doc:
        raise ValueError("suppression review inventory must be a dictionary with 'suppressions'")
    if set(known_doc) - {"schema", "suppressions"}:
        raise ValueError("unknown suppression review fields")
    if "schema" in known_doc and known_doc["schema"] != APPROVAL_SCHEMA:
        raise ValueError("unknown suppression approval schema")

    known_list = known_doc["suppressions"]
    if not isinstance(known_list, list):
        raise ValueError("suppression review inventory must be a list")

    # Detect malformed entries and duplicate inventory entries
    known_entries = []
    seen_entry_keys = set()
    for idx, raw_entry in enumerate(known_list):
        if not isinstance(raw_entry, dict):
            raise ValueError(f"suppression inventory entry at index {idx} must be a dict")
        if not raw_entry.get("path") or not raw_entry.get("kind"):
            raise ValueError(f"suppression inventory entry at index {idx} missing path or kind")
        fields = {"path", "line", "kind", "rule", "context", "owner", "reason", "review", "expiry", "disposition"}
        if set(raw_entry) - fields:
            raise ValueError("unknown suppression entry field")
        if not isinstance(raw_entry["path"], str) or raw_entry["kind"] not in SUPPRESSION_PATTERNS:
            raise ValueError("invalid suppression path or kind")
        if not isinstance(raw_entry.get("rule"), str):
            raise ValueError("invalid suppression rule")

        key_tuple = (
            raw_entry.get("path"),
            raw_entry.get("line"),
            raw_entry.get("kind"),
            normalize_rule(raw_entry.get("rule")),
            raw_entry.get("context", ""),
            
        )
        if key_tuple in seen_entry_keys:
            raise ValueError(f"duplicate suppression inventory entry at index {idx}: {key_tuple}")
        seen_entry_keys.add(key_tuple)

        # Validate date format if expiry is present
        expiry_val = raw_entry.get("expiry")
        if expiry_val is not None:
            if not isinstance(expiry_val, str):
                raise ValueError(f"invalid expiry date at index {idx}: {expiry_val}")
            try:
                date.fromisoformat(expiry_val)
            except (ValueError, TypeError) as error:
                raise ValueError(f"invalid expiry date at index {idx}: {expiry_val}") from error

        known_entries.append(dict(raw_entry, rule=normalize_rule(raw_entry.get("rule"))))

    # Match current suppressions with known entries
    unmatched_current = list(current)
    unmatched_known = list(known_entries)
    unchanged = []
    unapproved = []

    # Priority 1: Match by (path, kind, rule, context) where context is non-empty
    still_unmatched_current = []
    for curr in unmatched_current:
        curr_ctx = curr.get("context", "")
        match_idx = None
        if curr_ctx:
            for i, k in enumerate(unmatched_known):
                if (
                    k["path"] == curr["path"]
                    and k["kind"] == curr["kind"]
                    and k["rule"] == curr["rule"]
                    and k.get("context", "") == curr_ctx
                ):
                    match_idx = i
                    break
        if match_idx is not None:
            matched_k = unmatched_known.pop(match_idx)
            unchanged.append(curr)
            if not is_entry_approved(matched_k):
                unapproved.append(matched_k)
        else:
            still_unmatched_current.append(curr)

    still_unmatched_current3 = still_unmatched_current

    # Detect broadened rules: same path, kind, context (or line), but rule widened
    broadened = []
    remaining_current = []
    for curr in still_unmatched_current3:
        match_idx = None
        for i, k in enumerate(unmatched_known):
            if k["path"] == curr["path"] and k["kind"] == curr["kind"]:
                same_context = bool(curr.get("context") and curr.get("context") == k.get("context"))
                same_line = curr.get("line") == k.get("line")
                if same_context or same_line:
                    old_rules = set(re.split(r"[\s,]+", k["rule"].strip()))
                    new_rules = set(re.split(r"[\s,]+", curr["rule"].strip()))
                    if (curr["rule"] == "*" and k["rule"] != "*") or new_rules > old_rules:
                        match_idx = i
                        break
        if match_idx is not None:
            matched_k = unmatched_known.pop(match_idx)
            broadened.append({"previous": matched_k, "current": curr})
        else:
            remaining_current.append(curr)

    # Detect context_changed: same path, kind, rule, but context changed
    context_changed = []
    still_remaining_current = []
    for curr in remaining_current:
        match_idx = None
        for i, k in enumerate(unmatched_known):
            if (
                k["path"] == curr["path"]
                and k["kind"] == curr["kind"]
                and k["rule"] == curr["rule"]
                and bool(curr.get("context"))
                and bool(k.get("context"))
                and curr["context"] != k["context"]
            ):
                match_idx = i
                break
        if match_idx is not None:
            matched_k = unmatched_known.pop(match_idx)
            context_changed.append({"previous": matched_k, "current": curr})
        else:
            still_remaining_current.append(curr)

    added = still_remaining_current
    removed = unmatched_known

    blocking = bool(added or broadened or context_changed or unapproved)

    return {
        "schema": SCHEMA_V2,
        "blocking": blocking,
        "total_current": len(current),
        "added": added,
        "broadened": broadened,
        "context_changed": context_changed,
        "removed": removed,
        "unapproved_or_expired": unapproved,
        "unchanged": unchanged if known_file.is_file() else current,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scanner suppression inventory and drift control")
    parser.add_argument("--known", type=Path, default=None, help="Path to known suppressions JSON file")
    parser.add_argument("--root", type=Path, default=None, help="Path to repository root")
    args = parser.parse_args(argv)
    try:
        inv = build_inventory(
            known_file=args.known or KNOWN_SUPPRESSIONS_FILE,
            root=args.root or ROOT,
        )
    except (KeyError, TypeError, ValueError, OSError):
        print(json.dumps({"classification": "tool-failure", "error": "invalid suppression review inventory"}))
        return 2
    print(json.dumps(inv, indent=2, sort_keys=True))
    return 1 if inv["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
