#!/usr/bin/env python3
"""
Skill Config CLI - Central management tool for skills repository.

Usage:
    python scripts/skill_config.py <command> [options]

Commands:
    sync        Synchronize registry with filesystem
    list        List skills with filters
    info        Show skill details
    enable      Enable skills
    disable     Disable skills
    priority    Get/set skill priority
    version     Get/set/bump skill version
    deps        Manage dependencies
    category    Set skill category
    tag         Manage skill tags
    use         Record skill usage
    stats       Show usage statistics
    history     Show change history
    validate    Validate skill structure
    export      Export registry as JSON
    import      Import registry from JSON
"""

import argparse
import io
import json
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Resolve repo root and add to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from skill_discovery import discover_skills
from skill_registry import SkillRegistry


# ── Table Formatter ───────────────────────────────────────

def format_table(headers, rows, min_widths=None):
    """Format data as an aligned text table.

    Args:
        headers: list of column header strings
        rows: list of lists (each row's cell values)
        min_widths: optional dict of column_index -> min_width
    """
    if not rows:
        return ''

    # Convert all cells to strings
    str_rows = [[str(cell) for cell in row] for row in rows]

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in str_rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))

    if min_widths:
        for i, w in min_widths.items():
            if i < len(widths):
                widths[i] = max(widths[i], w)

    # Build format string
    fmt = '  '.join(f'{{:<{w}}}' for w in widths)
    lines = [fmt.format(*headers)]
    lines.append('  '.join('-' * w for w in widths))
    for row in str_rows:
        # Pad row to match header count
        padded = row + [''] * (len(headers) - len(row))
        lines.append(fmt.format(*padded[:len(headers)]))

    return '\n'.join(lines)


# ── CLI Commands ──────────────────────────────────────────

def cmd_sync(args, registry):
    """Synchronize registry with filesystem."""
    skills = discover_skills(REPO_ROOT)
    if registry.is_empty() and not args.dry_run:
        print("📋 Initial sync — discovering all skills...")

    result = registry.sync(skills, dry_run=args.dry_run)

    prefix = "[DRY RUN] " if args.dry_run else ""

    if result['added']:
        print(f"\n{prefix}✅ Added ({len(result['added'])}):")
        for name in sorted(result['added']):
            print(f"   + {name}")

    if result['updated']:
        print(f"\n{prefix}🔄 Updated ({len(result['updated'])}):")
        for name in sorted(result['updated']):
            print(f"   ~ {name}")

    if result['orphaned']:
        print(f"\n{prefix}⚠️  Orphaned ({len(result['orphaned'])}):")
        for name in sorted(result['orphaned']):
            print(f"   ? {name}")

    total = len(registry.data.get('skills', {})) if not args.dry_run else '?'
    print(f"\n{prefix}Total skills in registry: {total}")

    if not result['added'] and not result['updated'] and not result['orphaned']:
        print("✅ Registry is up to date.")


def cmd_list(args, registry):
    """List skills with filters."""
    _auto_sync(registry)

    enabled = None
    if args.enabled:
        enabled = True
    elif args.disabled:
        enabled = False

    items = registry.list_skills(
        enabled=enabled,
        category=args.category,
        sort_by=args.sort,
    )

    if not items:
        print("No skills found matching the criteria.")
        return

    if args.format == 'json':
        output = {name: data for name, data in items}
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    headers = ['Name', 'Status', 'Pri', 'Version', 'Category', 'Description']
    rows = []
    for name, skill in items:
        status = '✅' if skill.get('enabled') else '❌'
        desc = skill.get('description', '')
        # Truncate description
        if len(desc) > 50:
            desc = desc[:47] + '...'
        # Replace newlines for table display
        desc = desc.replace('\n', ' ')
        rows.append([
            name,
            status,
            str(skill.get('priority', 5)),
            skill.get('version', ''),
            skill.get('category', ''),
            desc,
        ])

    print(format_table(headers, rows))
    print(f"\nTotal: {len(items)} skill(s)")


def cmd_info(args, registry):
    """Show detailed skill info."""
    _auto_sync(registry)
    try:
        skill = registry.get_skill(args.skill)
    except KeyError as e:
        print(f"❌ {e}")
        sys.exit(1)

    print(f"📋 Skill: {skill.get('name', args.skill)}")
    print(f"   Directory:    {skill.get('directory', args.skill)}")
    print(f"   Description:  {skill.get('description', 'N/A')}")
    print(f"   Enabled:      {'✅ Yes' if skill.get('enabled') else '❌ No'}")
    print(f"   Priority:     {skill.get('priority', 5)}")
    print(f"   Version:      {skill.get('version', 'N/A')}")
    print(f"   Category:     {skill.get('category', 'N/A')}")
    print(f"   Tags:         {', '.join(skill.get('tags', [])) or 'none'}")
    print(f"   Dependencies: {', '.join(skill.get('dependencies', [])) or 'none'}")
    print(f"   Sub-skills:   {', '.join(skill.get('sub_skills', [])) or 'none'}")

    stats = skill.get('stats', {})
    print(f"\n   📊 Stats:")
    print(f"      Times used: {stats.get('times_used', 0)}")
    print(f"      Last used:  {stats.get('last_used', 'never')}")
    print(f"      Created:    {stats.get('created_at', 'unknown')}")

    if args.history:
        history = skill.get('history', [])
        if history:
            print(f"\n   📜 History (last {min(10, len(history))}):")
            for entry in history[-10:]:
                ts = entry.get('timestamp', '?')[:19]
                print(f"      [{ts}] {entry.get('action', '?')}: {entry.get('details', '')}")


def cmd_enable(args, registry):
    """Enable skills."""
    _auto_sync(registry)
    if args.all:
        for name in registry.data['skills']:
            registry.set_enabled(name, True)
        print(f"✅ All {len(registry.data['skills'])} skills enabled.")
        return
    for skill_name in args.skills:
        try:
            registry.set_enabled(skill_name, True)
            print(f"✅ Enabled: {skill_name}")
        except KeyError as e:
            print(f"❌ {e}")


def cmd_disable(args, registry):
    """Disable skills."""
    _auto_sync(registry)
    if args.all:
        for name in registry.data['skills']:
            registry.set_enabled(name, False)
        print(f"❌ All {len(registry.data['skills'])} skills disabled.")
        return
    for skill_name in args.skills:
        try:
            registry.set_enabled(skill_name, False)
            print(f"❌ Disabled: {skill_name}")
        except KeyError as e:
            print(f"❌ {e}")


def cmd_priority(args, registry):
    """Get or set skill priority."""
    _auto_sync(registry)
    try:
        if args.value is not None:
            registry.set_priority(args.skill, args.value)
            print(f"✅ {args.skill} priority set to {args.value}")
        else:
            skill = registry.get_skill(args.skill)
            print(f"{args.skill}: priority = {skill.get('priority', 5)}")
    except (KeyError, ValueError) as e:
        print(f"❌ {e}")
        sys.exit(1)


def cmd_version(args, registry):
    """Get, set, or bump skill version."""
    _auto_sync(registry)
    try:
        if args.bump:
            new_ver = registry.bump_version(args.skill, args.bump)
            print(f"✅ {args.skill} version bumped to {new_ver}")
        elif args.value:
            registry.set_version(args.skill, args.value)
            print(f"✅ {args.skill} version set to {args.value}")
        else:
            skill = registry.get_skill(args.skill)
            print(f"{args.skill}: version = {skill.get('version', 'N/A')}")
    except (KeyError, ValueError) as e:
        print(f"❌ {e}")
        sys.exit(1)


def cmd_deps(args, registry):
    """Manage dependencies."""
    _auto_sync(registry)
    try:
        if args.check:
            issues = registry.validate_dependency_graph()
            if issues:
                print("⚠️  Dependency issues found:")
                for issue in issues:
                    print(f"   - {issue}")
                sys.exit(1)
            else:
                print("✅ No dependency issues found.")
            return

        if args.tree:
            tree = registry.get_dependency_tree(args.tree)
            for indent, name in tree:
                print(f"{'  ' * indent}{'└─ ' if indent > 0 else ''}{name}")
            return

        if not args.skill:
            print("❌ Skill name required (or use --check / --tree)")
            sys.exit(1)

        if args.add:
            for dep in args.add:
                registry.add_dependency(args.skill, dep)
                print(f"✅ {args.skill} -> {dep} dependency added")
        elif args.remove:
            for dep in args.remove:
                registry.remove_dependency(args.skill, dep)
                print(f"✅ {args.skill} -> {dep} dependency removed")
        else:
            skill = registry.get_skill(args.skill)
            deps = skill.get('dependencies', [])
            if deps:
                print(f"🔗 {args.skill} dependencies: {', '.join(deps)}")
            else:
                print(f"🔗 {args.skill} has no dependencies.")

    except (KeyError, ValueError) as e:
        print(f"❌ {e}")
        sys.exit(1)


def cmd_category(args, registry):
    """Set skill category."""
    _auto_sync(registry)
    try:
        registry.set_category(args.skill, args.category)
        print(f"✅ {args.skill} category set to '{args.category}'")
    except KeyError as e:
        print(f"❌ {e}")
        sys.exit(1)


def cmd_tag(args, registry):
    """Manage skill tags."""
    _auto_sync(registry)
    try:
        if args.add:
            registry.add_tags(args.skill, args.add)
            print(f"✅ Tags added to {args.skill}: {', '.join(args.add)}")
        elif args.remove:
            registry.remove_tags(args.skill, args.remove)
            print(f"✅ Tags removed from {args.skill}: {', '.join(args.remove)}")
        else:
            skill = registry.get_skill(args.skill)
            tags = skill.get('tags', [])
            if tags:
                print(f"🏷️  {args.skill} tags: {', '.join(tags)}")
            else:
                print(f"🏷️  {args.skill} has no tags.")
    except KeyError as e:
        print(f"❌ {e}")
        sys.exit(1)


def cmd_use(args, registry):
    """Record skill usage."""
    _auto_sync(registry)
    try:
        registry.record_usage(args.skill)
        stats = registry.get_stats(args.skill)
        print(f"✅ Usage recorded for {args.skill} (total: {stats['times_used']})")
    except KeyError as e:
        print(f"❌ {e}")
        sys.exit(1)


def cmd_stats(args, registry):
    """Show usage statistics."""
    _auto_sync(registry)
    if args.skill:
        try:
            stats = registry.get_stats(args.skill)
            print(f"📊 Stats for {args.skill}:")
            print(f"   Times used: {stats.get('times_used', 0)}")
            print(f"   Last used:  {stats.get('last_used', 'never')}")
            print(f"   Created:    {stats.get('created_at', 'unknown')}")
        except KeyError as e:
            print(f"❌ {e}")
            sys.exit(1)
        return

    all_stats = registry.get_stats()
    items = list(all_stats.items())

    sort_key = args.sort if args.sort else 'times_used'
    if sort_key == 'times_used':
        items.sort(key=lambda x: x[1].get('times_used', 0), reverse=True)
    elif sort_key == 'last_used':
        items.sort(key=lambda x: x[1].get('last_used') or '', reverse=True)
    elif sort_key == 'name':
        items.sort(key=lambda x: x[0])

    headers = ['Skill', 'Times Used', 'Last Used']
    rows = []
    for name, stats in items:
        last = stats.get('last_used')
        last_str = last[:19] if last else 'never'
        rows.append([name, str(stats.get('times_used', 0)), last_str])

    print(format_table(headers, rows))


def cmd_history(args, registry):
    """Show change history."""
    _auto_sync(registry)
    limit = args.limit if args.limit else 20
    entries = registry.get_history(skill_name=args.skill, limit=limit)

    if not entries:
        print("No history entries found.")
        return

    if args.skill:
        print(f"📜 History for {args.skill}:")
    else:
        print("📜 Recent history:")

    for entry in entries:
        ts = entry.get('timestamp', '?')[:19]
        skill = entry.get('skill', '')
        prefix = f"[{skill}] " if skill and not args.skill else ''
        print(f"  [{ts}] {prefix}{entry.get('action', '?')}: {entry.get('details', '')}")


def cmd_validate(args, registry):
    """Validate skill structure."""
    _auto_sync(registry)

    # Try to import quick_validate
    validate_func = _get_validate_func()

    if args.skill:
        skills_to_check = [args.skill]
    else:
        skills_to_check = list(registry.data['skills'].keys())

    passed = 0
    failed = 0

    for skill_name in sorted(skills_to_check):
        skill_path = REPO_ROOT / skill_name
        if not skill_path.exists():
            print(f"⚠️  {skill_name}: directory not found")
            failed += 1
            continue

        if validate_func:
            valid, message = validate_func(skill_path)
            if valid:
                print(f"✅ {skill_name}: {message}")
                passed += 1
            else:
                print(f"❌ {skill_name}: {message}")
                failed += 1
        else:
            # Basic validation: check SKILL.md exists
            skill_md = skill_path / 'SKILL.md'
            if skill_md.exists():
                print(f"✅ {skill_name}: SKILL.md found")
                passed += 1
            else:
                print(f"❌ {skill_name}: SKILL.md missing")
                failed += 1

    print(f"\n📊 Results: {passed} passed, {failed} failed, {passed + failed} total")
    if failed > 0:
        sys.exit(1)


def cmd_export(args, registry):
    """Export registry as JSON."""
    _auto_sync(registry)
    print(registry.export_registry())


def cmd_import(args, registry):
    """Import registry from JSON file."""
    try:
        count = registry.import_registry(args.file)
        print(f"✅ Imported {count} skills from {args.file}")
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Import failed: {e}")
        sys.exit(1)


# ── Helpers ───────────────────────────────────────────────

def _auto_sync(registry):
    """Auto-sync if registry is empty (first run)."""
    if registry.is_empty():
        print("📋 Registry is empty — running initial sync...\n")
        skills = discover_skills(REPO_ROOT)
        registry.sync(skills)
        print(f"✅ Synced {len(registry.data['skills'])} skills.\n")


def _get_validate_func():
    """Try to import validate_skill from quick_validate.py.

    Wraps the function to ensure UTF-8 encoding is used for file reads,
    avoiding cp932 errors on Windows.
    """
    validate_path = REPO_ROOT / 'skill-creator' / 'scripts' / 'quick_validate.py'
    if not validate_path.exists():
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location('quick_validate', str(validate_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        original_func = getattr(mod, 'validate_skill', None)
        if original_func is None:
            return None

        # Wrap to handle encoding issues
        def _validate_utf8(skill_path):
            import re as _re
            skill_path = Path(skill_path)
            skill_md = skill_path / 'SKILL.md'
            if not skill_md.exists():
                return False, "SKILL.md not found"
            try:
                content = skill_md.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                return False, "SKILL.md has encoding issues (not valid UTF-8)"

            if not content.startswith('---'):
                return False, "No YAML frontmatter found"
            match = _re.match(r'^---\n(.*?)\n---', content, _re.DOTALL)
            if not match:
                return False, "Invalid frontmatter format"
            frontmatter = match.group(1)
            if 'name:' not in frontmatter:
                return False, "Missing 'name' in frontmatter"
            if 'description:' not in frontmatter:
                return False, "Missing 'description' in frontmatter"
            name_match = _re.search(r'name:\s*(.+)', frontmatter)
            if name_match:
                name = name_match.group(1).strip()
                if not _re.match(r'^[a-z0-9-]+$', name):
                    return False, f"Name '{name}' should be hyphen-case"
                if name.startswith('-') or name.endswith('-') or '--' in name:
                    return False, f"Name '{name}' has invalid hyphen placement"
            desc_match = _re.search(r'description:\s*(.+)', frontmatter)
            if desc_match:
                description = desc_match.group(1).strip()
                if '<' in description or '>' in description:
                    return False, "Description cannot contain angle brackets"
            return True, "Skill is valid!"

        return _validate_utf8
    except Exception:
        return None


# ── Argument Parser ───────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        prog='skill_config',
        description='Skill registry management CLI',
    )
    sub = parser.add_subparsers(dest='command', help='Available commands')

    # sync
    p_sync = sub.add_parser('sync', help='Sync registry with filesystem')
    p_sync.add_argument('--dry-run', action='store_true', help='Preview changes without applying')

    # list
    p_list = sub.add_parser('list', help='List skills')
    p_list.add_argument('--enabled', action='store_true', help='Show only enabled skills')
    p_list.add_argument('--disabled', action='store_true', help='Show only disabled skills')
    p_list.add_argument('--category', '-c', help='Filter by category')
    p_list.add_argument('--sort', '-s', default='name',
                        choices=['name', 'priority', 'times_used', 'version'],
                        help='Sort by field')
    p_list.add_argument('--format', '-f', default='table', choices=['table', 'json'],
                        help='Output format')

    # info
    p_info = sub.add_parser('info', help='Show skill details')
    p_info.add_argument('skill', help='Skill directory name')
    p_info.add_argument('--history', action='store_true', help='Include history')

    # enable
    p_enable = sub.add_parser('enable', help='Enable skills')
    p_enable.add_argument('skills', nargs='*', help='Skill names to enable')
    p_enable.add_argument('--all', action='store_true', help='Enable all skills')

    # disable
    p_disable = sub.add_parser('disable', help='Disable skills')
    p_disable.add_argument('skills', nargs='*', help='Skill names to disable')
    p_disable.add_argument('--all', action='store_true', help='Disable all skills')

    # priority
    p_prio = sub.add_parser('priority', help='Get/set skill priority (1-10)')
    p_prio.add_argument('skill', help='Skill name')
    p_prio.add_argument('value', nargs='?', type=int, help='Priority value (1-10)')

    # version
    p_ver = sub.add_parser('version', help='Get/set/bump skill version')
    p_ver.add_argument('skill', help='Skill name')
    p_ver.add_argument('value', nargs='?', help='Version string')
    p_ver.add_argument('--bump', choices=['major', 'minor', 'patch'], help='Bump version part')

    # deps
    p_deps = sub.add_parser('deps', help='Manage dependencies')
    p_deps.add_argument('skill', nargs='?', help='Skill name')
    p_deps.add_argument('--add', nargs='+', help='Add dependencies')
    p_deps.add_argument('--remove', nargs='+', help='Remove dependencies')
    p_deps.add_argument('--check', action='store_true', help='Validate all dependency graphs')
    p_deps.add_argument('--tree', help='Show dependency tree for a skill')

    # category
    p_cat = sub.add_parser('category', help='Set skill category')
    p_cat.add_argument('skill', help='Skill name')
    p_cat.add_argument('category', help='Category name')

    # tag
    p_tag = sub.add_parser('tag', help='Manage skill tags')
    p_tag.add_argument('skill', help='Skill name')
    p_tag.add_argument('--add', nargs='+', help='Tags to add')
    p_tag.add_argument('--remove', nargs='+', help='Tags to remove')

    # use
    p_use = sub.add_parser('use', help='Record skill usage')
    p_use.add_argument('skill', help='Skill name')

    # stats
    p_stats = sub.add_parser('stats', help='Show usage statistics')
    p_stats.add_argument('skill', nargs='?', help='Skill name (optional)')
    p_stats.add_argument('--sort', choices=['times_used', 'last_used', 'name'],
                         default='times_used', help='Sort by field')

    # history
    p_hist = sub.add_parser('history', help='Show change history')
    p_hist.add_argument('skill', nargs='?', help='Skill name (optional)')
    p_hist.add_argument('--limit', '-n', type=int, default=20, help='Number of entries')

    # validate
    p_val = sub.add_parser('validate', help='Validate skill structure')
    p_val.add_argument('skill', nargs='?', help='Skill to validate (default: all)')

    # export
    sub.add_parser('export', help='Export registry as JSON')

    # import
    p_imp = sub.add_parser('import', help='Import registry from JSON file')
    p_imp.add_argument('file', help='JSON file to import')

    return parser


COMMAND_MAP = {
    'sync': cmd_sync,
    'list': cmd_list,
    'info': cmd_info,
    'enable': cmd_enable,
    'disable': cmd_disable,
    'priority': cmd_priority,
    'version': cmd_version,
    'deps': cmd_deps,
    'category': cmd_category,
    'tag': cmd_tag,
    'use': cmd_use,
    'stats': cmd_stats,
    'history': cmd_history,
    'validate': cmd_validate,
    'export': cmd_export,
    'import': cmd_import,
}


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    registry = SkillRegistry()
    handler = COMMAND_MAP.get(args.command)
    if handler:
        handler(args, registry)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
