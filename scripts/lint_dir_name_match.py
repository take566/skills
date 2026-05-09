#!/usr/bin/env python3
"""Lint: ensure SKILL.md frontmatter `name` matches its directory name.

Catches the regression class where a skill is renamed at the directory level
but the frontmatter `name` is left dangling (or vice versa). The two are
expected to be the same identifier across the Anthropic Skills surface.

Exit code: 0 on full match, 1 on any mismatch / missing name.
"""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from skill_discovery import discover_skills


def main() -> int:
    repo_root = SCRIPT_DIR.parent
    skills = discover_skills(repo_root)

    mismatches = []
    for skill in skills:
        directory = skill["directory"]
        name = skill["frontmatter"].get("name", "")
        if not name:
            mismatches.append((directory, "<missing>"))
        elif name != directory:
            mismatches.append((directory, name))

    if mismatches:
        print("ERROR: SKILL.md frontmatter `name` does not match directory:")
        for directory, name in mismatches:
            print(f"  - {directory}/SKILL.md => name: {name}")
        print(f"\n{len(mismatches)} mismatch(es) found out of {len(skills)} skills.")
        return 1

    print(f"OK: all {len(skills)} skills have name == directory.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
