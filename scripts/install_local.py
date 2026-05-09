#!/usr/bin/env python3
"""Install skills from this repository into a local Claude Code skills directory.

Default target is ``~/.claude/skills``. On Windows the default install method is
``copy`` (symlinks require Developer Mode or administrator rights); on POSIX the
default is ``link`` so that repository updates propagate without re-running the
script. Override with ``--method``.

Examples:
    python scripts/install_local.py --all
    python scripts/install_local.py --skill code-quality --skill cicd
    python scripts/install_local.py --all --dry-run
    python scripts/install_local.py --all --force
    python scripts/install_local.py --skill devops --method link
"""

from __future__ import annotations

import argparse
import io
import os
import shutil
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


DEFAULT_TARGET = Path.home() / ".claude" / "skills"


def resolve_method(arg: str) -> str:
    if arg != "auto":
        return arg
    return "copy" if os.name == "nt" else "link"


def filter_skills(all_skills, names):
    if not names:
        return all_skills
    by_name = {s["directory"]: s for s in all_skills}
    selected = []
    missing = []
    for name in names:
        if name in by_name:
            selected.append(by_name[name])
        else:
            missing.append(name)
    if missing:
        available = ", ".join(sorted(by_name)) or "(none)"
        sys.exit(
            f"ERROR: skill(s) not found: {', '.join(missing)}\n"
            f"Available: {available}"
        )
    return selected


def install_one(skill, target_dir: Path, method: str, force: bool, dry_run: bool):
    name = skill["directory"]
    src = Path(skill["path"]).resolve()
    dst = (target_dir / name).resolve()

    exists = dst.exists() or dst.is_symlink()
    if exists and not force:
        return "skipped", f"{name}: target already exists at {dst} (use --force to overwrite)"

    if dry_run:
        action = "replace" if exists else "create"
        return "planned", f"{name}: would {action} via {method} at {dst}"

    if exists and force:
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        else:
            shutil.rmtree(dst)

    if method == "link":
        os.symlink(str(src), str(dst), target_is_directory=True)
        return "installed", f"{name}: linked {dst} -> {src}"
    elif method == "copy":
        shutil.copytree(str(src), str(dst))
        return "installed", f"{name}: copied to {dst}"
    else:
        return "failed", f"{name}: unknown method '{method}'"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--all", action="store_true", help="Install every discovered skill")
    selector.add_argument("--skill", action="append", default=[], help="Install a specific skill (repeatable)")

    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET,
                        help=f"Target directory (default: {DEFAULT_TARGET})")
    parser.add_argument("--method", choices=("auto", "link", "copy"), default="auto",
                        help="Install method (default: auto -> copy on Windows, link on POSIX)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing target entries")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without making changes")

    args = parser.parse_args()
    method = resolve_method(args.method)

    skills = discover_skills(REPO_ROOT)
    if not skills:
        sys.exit("ERROR: no skills discovered in repo")

    selected = skills if args.all else filter_skills(skills, args.skill)
    if not selected:
        sys.exit("ERROR: no skills selected")

    target = args.target.expanduser().resolve()
    if not args.dry_run:
        target.mkdir(parents=True, exist_ok=True)

    print(f"Source repo : {REPO_ROOT}")
    print(f"Target dir  : {target}")
    print(f"Method      : {method}{' (auto)' if args.method == 'auto' else ''}")
    print(f"Skills      : {len(selected)}")
    print(f"Mode        : {'DRY-RUN' if args.dry_run else 'EXECUTE'}")
    print()

    counts = {"installed": 0, "skipped": 0, "planned": 0, "failed": 0}
    for skill in selected:
        try:
            status, message = install_one(skill, target, method, args.force, args.dry_run)
        except OSError as e:
            status, message = "failed", f"{skill['directory']}: {e.__class__.__name__}: {e}"
        counts[status] = counts.get(status, 0) + 1
        prefix = {
            "installed": "OK",
            "planned":   "DRY",
            "skipped":   "SKIP",
            "failed":    "FAIL",
        }[status]
        print(f"  [{prefix}] {message}")

    print()
    summary = ", ".join(f"{k}: {v}" for k, v in counts.items() if v)
    print(f"Done. {summary}")
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
