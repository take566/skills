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


def collect_files(
    skill_dir: Path,
    top_folder: str,
    exclude_top_dirs: set[str] | None = None,
) -> list[tuple[str, bytes, str]]:
    """Return [(relative_path, content, mime_type), ...] for a skill bundle.

    Each path is prefixed with ``top_folder`` so the API receives a bundle
    under a single top-level folder (with SKILL.md at its root), e.g.
    ``code-quality/SKILL.md`` and ``code-quality/reference/commit.md``.

    ``exclude_top_dirs`` lets a parent skill exclude sub-skill directories
    (each containing its own SKILL.md, which the API forbids in one bundle).
    """
    bundle = []
    skill_dir = skill_dir.resolve()
    exclude_top_dirs = exclude_top_dirs or set()
    for f in skill_dir.rglob("*"):
        if not f.is_file():
            continue
        rel_parts = f.relative_to(skill_dir).parts
        if any(part in EXCLUDE_PATH_PARTS for part in rel_parts):
            continue
        if rel_parts and rel_parts[0] in exclude_top_dirs:
            continue
        rel = f"{top_folder}/{f.relative_to(skill_dir).as_posix()}"
        mime, _ = mimetypes.guess_type(rel)
        if mime is None:
            mime = "application/octet-stream"
        bundle.append((rel, f.read_bytes(), mime))
    return bundle


def expand_targets(skills: list[dict]) -> list[dict]:
    """Expand each skill into one or more publish targets.

    A skill with sub-skills (e.g. document-processing/{docx,pdf,pptx,xlsx})
    yields one target per unit: the parent (sub directories excluded) plus
    each sub-skill as its own target. The synthesized name for a sub-skill
    is ``<parent>-<sub>`` (e.g. ``document-processing-docx``) so it gets a
    unique state-file key and display title.
    """
    targets = []
    for skill in skills:
        sub_skills = skill.get("sub_skills") or []
        if sub_skills:
            sub_dir_names = {s["directory"] for s in sub_skills}
            targets.append({
                "name": skill["directory"],
                "skill_dir": Path(skill["path"]),
                "frontmatter": skill["frontmatter"],
                "top_folder": skill["directory"],
                "exclude_top_dirs": sub_dir_names,
            })
            for sub in sub_skills:
                synthesized = f"{skill['directory']}-{sub['directory']}"
                # The API requires top_folder == frontmatter.name. Sub-skill
                # frontmatter names are short (e.g. "docx") so we use that
                # for the upload folder, while keeping the synthesized name
                # as the state-file key to namespace it locally.
                sub_fm_name = sub["frontmatter"].get("name") or sub["directory"]
                targets.append({
                    "name": synthesized,
                    "skill_dir": Path(sub["path"]),
                    "frontmatter": sub["frontmatter"],
                    "top_folder": sub_fm_name,
                    "exclude_top_dirs": set(),
                })
        else:
            targets.append({
                "name": skill["directory"],
                "skill_dir": Path(skill["path"]),
                "frontmatter": skill["frontmatter"],
                "top_folder": skill["directory"],
                "exclude_top_dirs": set(),
            })
    return targets


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


def publish_one(client, target: dict, prefix: str, dry_run: bool):
    name = target["name"]
    bundle = collect_files(
        target["skill_dir"],
        top_folder=target["top_folder"],
        exclude_top_dirs=target["exclude_top_dirs"],
    )

    expected_root = f"{target['top_folder']}/SKILL.md"
    has_skill_md = any(rel == expected_root for rel, _, _ in bundle)
    if not has_skill_md:
        return "failed", f"{name}: SKILL.md not found at {expected_root}", None

    fm = target["frontmatter"]
    raw_title = fm.get("display-title") or name
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

    targets = expand_targets(selected)
    state = load_state(args.state_file)

    print(f"Source repo : {REPO_ROOT}")
    print(f"State file  : {args.state_file}")
    print(f"Skills      : {len(selected)} (expanded to {len(targets)} bundles)")
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
    for target in targets:
        name = target["name"]
        if name in state and not args.force_recreate and not args.dry_run:
            counts["skipped"] += 1
            print(f"  [SKIP] {name}: already published (id={state[name]}) — use --force-recreate to override")
            continue

        try:
            status, message, new_id = publish_one(client, target, args.display_title_prefix, args.dry_run)
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
