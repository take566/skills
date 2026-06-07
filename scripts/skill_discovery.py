#!/usr/bin/env python3
"""
Skill Discovery - Filesystem scanning and frontmatter parsing for skills repository.
"""

import re
from pathlib import Path

EXCLUDED_DIRS = {
    '_archive', 'reference', 'data', 'gws-cli-skills',
    'self-improving-agent', 'tapestry',
    'template-skill', '.git', 'scripts', '.cursor',
    'node_modules', '__pycache__',
}


def parse_frontmatter(skill_md_path):
    """Parse YAML frontmatter from a SKILL.md file using regex.

    Handles:
    - Standard key: value pairs
    - Multiline | (literal block scalar) values
    - Quoted value stripping

    Args:
        skill_md_path: Path to SKILL.md file

    Returns:
        dict with parsed frontmatter fields, empty dict if no frontmatter
    """
    skill_md_path = Path(skill_md_path)
    if not skill_md_path.exists():
        return {}

    content = skill_md_path.read_text(encoding='utf-8')
    if not content.startswith('---'):
        return {}

    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}

    frontmatter_text = match.group(1)
    result = {}
    lines = frontmatter_text.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]
        # Match top-level key: value
        key_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)', line)
        if key_match:
            key = key_match.group(1).strip()
            value = key_match.group(2).strip()

            if value == '|':
                # Multiline literal block scalar
                block_lines = []
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    # Stop at next top-level key or empty unindented line
                    if next_line and not next_line[0].isspace():
                        break
                    block_lines.append(next_line)
                    i += 1
                # Dedent and join
                text = '\n'.join(block_lines)
                # Remove common leading whitespace
                text = re.sub(r'^\n+', '', text)
                text = re.sub(r'\n+$', '', text)
                if block_lines:
                    # Find minimum indentation
                    indents = [len(l) - len(l.lstrip()) for l in block_lines if l.strip()]
                    if indents:
                        min_indent = min(indents)
                        text = '\n'.join(
                            l[min_indent:] if len(l) > min_indent else l.strip()
                            for l in block_lines
                        ).strip()
                result[key] = text
                continue
            elif value.startswith('[') and value.endswith(']'):
                # Inline list: [item1, item2]
                inner = value[1:-1].strip()
                if inner:
                    result[key] = [_strip_quotes(item.strip()) for item in inner.split(',')]
                else:
                    result[key] = []
            elif value == '':
                result[key] = ''
            else:
                result[key] = _strip_quotes(value)
        i += 1

    return result


def _strip_quotes(value):
    """Strip surrounding quotes from a string value."""
    if len(value) >= 2:
        if (value[0] == '"' and value[-1] == '"') or \
           (value[0] == "'" and value[-1] == "'"):
            return value[1:-1]
    return value


def discover_skills(repo_root):
    """Scan repository root for skill directories containing SKILL.md.

    Args:
        repo_root: Path to the repository root

    Returns:
        list of dicts with keys: directory, path, frontmatter, sub_skills
    """
    repo_root = Path(repo_root)
    skills = []

    for item in sorted(repo_root.iterdir()):
        if not item.is_dir():
            continue
        if item.name in EXCLUDED_DIRS or item.name.startswith('.'):
            continue

        skill_md = item / 'SKILL.md'
        if not skill_md.exists():
            continue

        frontmatter = parse_frontmatter(skill_md)
        sub_skills = discover_sub_skills(item)

        skills.append({
            'directory': item.name,
            'path': str(item),
            'frontmatter': frontmatter,
            'sub_skills': sub_skills,
        })

    return skills


def discover_sub_skills(skill_dir):
    """Discover sub-skills within a skill directory.

    Sub-skills are subdirectories that also contain a SKILL.md file.
    Example: document-processing/docx, document-processing/pdf

    Args:
        skill_dir: Path to the parent skill directory

    Returns:
        list of dicts with keys: directory, path, frontmatter
    """
    skill_dir = Path(skill_dir)
    sub_skills = []

    for item in sorted(skill_dir.iterdir()):
        if not item.is_dir():
            continue
        if item.name in EXCLUDED_DIRS or item.name.startswith('.'):
            continue
        # Skip common non-skill subdirectories
        if item.name in ('scripts', 'references', 'assets', 'templates', '__pycache__'):
            continue

        sub_skill_md = item / 'SKILL.md'
        if not sub_skill_md.exists():
            continue

        frontmatter = parse_frontmatter(sub_skill_md)
        sub_skills.append({
            'directory': item.name,
            'path': str(item),
            'frontmatter': frontmatter,
        })

    return sub_skills
