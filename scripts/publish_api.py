#!/usr/bin/env python3
"""Publish skills from this repository to the Anthropic Skills API.

Uses the Anthropic Python SDK (``client.beta.skills.create``). Each skill
directory is bundled and uploaded with the directory's ``SKILL.md`` at the root.
A local state file tracks already-published skills to skip duplicate creates;
pass ``--force-recreate`` to override.

Required environment:
    ANTHROPIC_API_KEY    Anthropic API key (Skills API beta access required)

Examples:
    python scripts/publish_api.py --skill code-quality --dry-run
    python scripts/publish_api.py --skill code-quality
    python scripts/publish_api.py --all
    python scripts/publish_api.py --skill code-quality --force-recreate
    python scripts/publish_api.py --all --display-title-prefix "[staging] "
"""

from __future__ import annotations

import argparse
import io
import json
import mimetypes
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from skill_discovery import discover_skills

SKILLS_BETA = "skills-2025-10-02"
DEFAULT_STATE_FILE = REPO_ROOT / "data" / "api_skill_ids.json"
EXCLUDE_PATH_PARTS = {"__pycache__", ".git", ".cursor", "node_modules"}


def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    if os.name == "nt" and path.exists():
        path.unlink()
    tmp.rename(path)


def collect_files(skill_dir: Path) -> list[tuple[str, bytes, str]]:
    """Return [(relative_path, content, mime_type), ...] for a skill bundle."""
    bundle = []
    skill_dir = skill_dir.resolve()
    for f in skill_dir.rglob("*"):
        if not f.is_file():
            continue
        if any(part in EXCLUDE_PATH_PARTS for part in f.relative_to(skill_dir).parts):
            continue
        rel = f.relative_to(skill_dir).as_posix()
        mime, _ = mimetypes.guess_type(rel)
        if mime is None:
            mime = "application/octet-stream"
        bundle.append((rel, f.read_bytes(), mime))
    return bundle


def filter_skills(all_skills, names):
    if not names:
        return all_skills
    by_name = {s["directory"]: s for s in all_skills}
    selected, missing = [], []
    for n in names:
        if n in by_name:
            selected.append(by_name[n])
        else:
            missing.append(n)
    if missing:
        sys.exit(f"ERROR: skill(s) not found: {', '.join(missing)}")
    return selected


def publish_one(client, skill, prefix: str, dry_run: bool):
    name = skill["directory"]
    skill_dir = Path(skill["path"])
    bundle = collect_files(skill_dir)

    has_skill_md = any(rel == "SKILL.md" for rel, _, _ in bundle)
    if not has_skill_md:
        return "failed", f"{name}: SKILL.md not found at root of {skill_dir}", None

    fm = skill["frontmatter"]
    raw_title = fm.get("display-title") or fm.get("name") or name
    display_title = f"{prefix}{raw_title}"

    if dry_run:
        files_summary = ", ".join(rel for rel, _, _ in bundle[:6])
        if len(bundle) > 6:
            files_summary += f", ... (+{len(bundle) - 6} more)"
        return "planned", (
            f"{name}: would POST /v1/skills | display_title={display_title!r} | "
            f"{len(bundle)} files [{files_summary}]"
        ), None

    files_param = [(rel, content, mime) for rel, content, mime in bundle]
    response = client.beta.skills.create(
        display_title=display_title,
        files=files_param,
        betas=[SKILLS_BETA],
    )
    skill_id = getattr(response, "id", None)
    return "created", f"{name}: id={skill_id}", skill_id


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--all", action="store_true", help="Publish every discovered skill")
    selector.add_argument("--skill", action="append", default=[], help="Publish a specific skill (repeatable)")

    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE,
                        help=f"Path to JSON state file tracking published skill IDs (default: {DEFAULT_STATE_FILE})")
    parser.add_argument("--force-recreate", action="store_true",
                        help="Re-create even if the skill is already in the state file")
    parser.add_argument("--display-title-prefix", default="",
                        help="Prefix prepended to each skill's display_title")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the planned request without calling the API")

    args = parser.parse_args()

    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ERROR: ANTHROPIC_API_KEY is not set")

    skills = discover_skills(REPO_ROOT)
    selected = skills if args.all else filter_skills(skills, args.skill)
    if not selected:
        sys.exit("ERROR: no skills selected")

    state = load_state(args.state_file)

    print(f"Source repo : {REPO_ROOT}")
    print(f"State file  : {args.state_file}")
    print(f"Skills      : {len(selected)}")
    print(f"Mode        : {'DRY-RUN' if args.dry_run else 'EXECUTE'}")
    print(f"Beta        : {SKILLS_BETA}")
    print()

    client = None
    if not args.dry_run:
        try:
            from anthropic import Anthropic
        except ImportError:
            sys.exit("ERROR: 'anthropic' package not installed. pip install anthropic")
        client = Anthropic()

    counts = {"created": 0, "skipped": 0, "planned": 0, "failed": 0}
    for skill in selected:
        name = skill["directory"]
        if name in state and not args.force_recreate and not args.dry_run:
            counts["skipped"] += 1
            print(f"  [SKIP] {name}: already published (id={state[name]}) — use --force-recreate to override")
            continue

        try:
            status, message, new_id = publish_one(client, skill, args.display_title_prefix, args.dry_run)
        except Exception as exc:  # noqa: BLE001 - surface any SDK error
            status = "failed"
            message = f"{name}: {exc.__class__.__name__}: {exc}"
            new_id = None

        counts[status] = counts.get(status, 0) + 1
        prefix = {"created": "OK", "planned": "DRY", "skipped": "SKIP", "failed": "FAIL"}[status]
        print(f"  [{prefix}] {message}")

        if new_id and not args.dry_run:
            state[name] = new_id
            save_state(args.state_file, state)

    print()
    summary = ", ".join(f"{k}: {v}" for k, v in counts.items() if v)
    print(f"Done. {summary}")
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
