#!/usr/bin/env python3
"""
Skill Registry - Persistent registry management for skills.
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent.parent / 'data' / 'skill_registry.json'

EMPTY_REGISTRY = {
    "$schema": "skill-registry-v1",
    "last_synced": None,
    "skills": {},
    "categories": [],
}

MAX_HISTORY_ENTRIES = 50


class SkillRegistry:
    """Manages the persistent skill registry JSON file."""

    def __init__(self, registry_path=None):
        self.path = Path(registry_path) if registry_path else DEFAULT_REGISTRY_PATH
        self._data = None

    def _load(self):
        """Load registry from JSON file."""
        if self.path.exists():
            self._data = json.loads(self.path.read_text(encoding='utf-8'))
        else:
            self._data = json.loads(json.dumps(EMPTY_REGISTRY))

    def _ensure_loaded(self):
        if self._data is None:
            self._load()

    @property
    def data(self):
        self._ensure_loaded()
        return self._data

    def save(self):
        """Save registry to JSON file with atomic write."""
        self._ensure_loaded()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix('.tmp')
        tmp_path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding='utf-8',
        )
        # Atomic rename (on Windows, need to remove target first)
        if os.name == 'nt' and self.path.exists():
            self.path.unlink()
        tmp_path.rename(self.path)

    def _now_iso(self):
        return datetime.now(timezone.utc).isoformat()

    # ── Sync ──────────────────────────────────────────────

    def sync(self, discovered_skills, dry_run=False):
        """Synchronize registry with discovered skills from filesystem.

        Args:
            discovered_skills: list of dicts from discover_skills()
            dry_run: if True, report changes without applying

        Returns:
            dict with keys: added, updated, orphaned (lists of skill directory names)
        """
        self._ensure_loaded()
        existing = set(self.data['skills'].keys())
        discovered_names = set()
        added = []
        updated = []

        for skill in discovered_skills:
            dir_name = skill['directory']
            discovered_names.add(dir_name)
            fm = skill.get('frontmatter', {})
            sub_skills = [s['directory'] for s in skill.get('sub_skills', [])]

            if dir_name not in self.data['skills']:
                # New skill
                added.append(dir_name)
                if not dry_run:
                    self.data['skills'][dir_name] = self._create_skill_entry(
                        dir_name, fm, sub_skills
                    )
            else:
                # Existing skill — update frontmatter-derived fields
                entry = self.data['skills'][dir_name]
                changed = False
                new_name = fm.get('name', dir_name)
                new_desc = fm.get('description', '')
                if entry.get('name') != new_name:
                    entry['name'] = new_name
                    changed = True
                if entry.get('description') != new_desc:
                    entry['description'] = new_desc
                    changed = True
                if entry.get('sub_skills') != sub_skills:
                    entry['sub_skills'] = sub_skills
                    changed = True
                if changed:
                    updated.append(dir_name)
                    if not dry_run:
                        self._add_history(dir_name, 'updated', 'Synced from filesystem')

        orphaned = list(existing - discovered_names)

        if not dry_run:
            # Mark orphaned skills
            for name in orphaned:
                self._add_history(name, 'orphaned', 'Not found on filesystem')

            # Update categories from all skills
            self._rebuild_categories()
            self.data['last_synced'] = self._now_iso()
            self.save()

        return {'added': added, 'updated': updated, 'orphaned': orphaned}

    def _create_skill_entry(self, dir_name, frontmatter, sub_skills):
        """Create a new skill registry entry."""
        now = self._now_iso()
        entry = {
            'name': frontmatter.get('name', dir_name),
            'directory': dir_name,
            'description': frontmatter.get('description', ''),
            'enabled': True,
            'priority': 5,
            'version': frontmatter.get('version', '1.0.0'),
            'category': frontmatter.get('category', ''),
            'tags': [],
            'dependencies': [],
            'sub_skills': sub_skills,
            'stats': {
                'times_used': 0,
                'last_used': None,
                'created_at': now,
            },
            'history': [{
                'timestamp': now,
                'action': 'discovered',
                'details': 'Initial discovery from filesystem',
            }],
        }
        return entry

    def _rebuild_categories(self):
        """Rebuild categories list from all skills."""
        cats = set()
        for skill in self.data['skills'].values():
            cat = skill.get('category', '')
            if cat:
                cats.add(cat)
        self.data['categories'] = sorted(cats)

    # ── Enable / Disable ──────────────────────────────────

    def set_enabled(self, skill_name, enabled):
        """Enable or disable a skill."""
        self._ensure_skill(skill_name)
        self.data['skills'][skill_name]['enabled'] = enabled
        action = 'enabled' if enabled else 'disabled'
        self._add_history(skill_name, action, f'Skill {action}')
        self.save()

    # ── Priority ──────────────────────────────────────────

    def set_priority(self, skill_name, priority):
        """Set skill priority (1-10)."""
        if not (1 <= priority <= 10):
            raise ValueError("Priority must be between 1 and 10")
        self._ensure_skill(skill_name)
        old = self.data['skills'][skill_name]['priority']
        self.data['skills'][skill_name]['priority'] = priority
        self._add_history(skill_name, 'priority_changed', f'{old} -> {priority}')
        self.save()

    # ── Version ───────────────────────────────────────────

    def set_version(self, skill_name, version):
        """Set skill version string."""
        self._ensure_skill(skill_name)
        old = self.data['skills'][skill_name]['version']
        self.data['skills'][skill_name]['version'] = version
        self._add_history(skill_name, 'version_changed', f'{old} -> {version}')
        self.save()

    def bump_version(self, skill_name, part='patch'):
        """Bump version (major, minor, patch)."""
        self._ensure_skill(skill_name)
        current = self.data['skills'][skill_name].get('version', '1.0.0')
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)', current)
        if not match:
            raise ValueError(f"Cannot bump non-semver version: {current}")
        major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if part == 'major':
            major += 1
            minor = 0
            patch = 0
        elif part == 'minor':
            minor += 1
            patch = 0
        elif part == 'patch':
            patch += 1
        else:
            raise ValueError(f"Invalid version part: {part}. Use major, minor, or patch")
        new_version = f"{major}.{minor}.{patch}"
        self.set_version(skill_name, new_version)
        return new_version

    # ── Dependencies ──────────────────────────────────────

    def add_dependency(self, skill_name, dependency):
        """Add a dependency to a skill."""
        self._ensure_skill(skill_name)
        if dependency not in self.data['skills']:
            raise ValueError(f"Dependency '{dependency}' not found in registry")
        if dependency == skill_name:
            raise ValueError("A skill cannot depend on itself")
        deps = self.data['skills'][skill_name]['dependencies']
        if dependency not in deps:
            deps.append(dependency)
            self._add_history(skill_name, 'dependency_added', f'Added dependency: {dependency}')
            # Check for circular dependencies after adding
            cycle = self._find_cycle(skill_name)
            if cycle:
                deps.remove(dependency)
                raise ValueError(f"Circular dependency detected: {' -> '.join(cycle)}")
            self.save()

    def remove_dependency(self, skill_name, dependency):
        """Remove a dependency from a skill."""
        self._ensure_skill(skill_name)
        deps = self.data['skills'][skill_name]['dependencies']
        if dependency in deps:
            deps.remove(dependency)
            self._add_history(skill_name, 'dependency_removed', f'Removed dependency: {dependency}')
            self.save()

    def validate_dependency_graph(self):
        """Check all dependencies for issues.

        Returns:
            list of issue strings (empty = valid)
        """
        self._ensure_loaded()
        issues = []
        all_skills = set(self.data['skills'].keys())

        for name, skill in self.data['skills'].items():
            for dep in skill.get('dependencies', []):
                if dep not in all_skills:
                    issues.append(f"{name}: dependency '{dep}' not found")
                if dep == name:
                    issues.append(f"{name}: self-dependency")

            # Check for cycles from this node
            cycle = self._find_cycle(name)
            if cycle:
                cycle_str = ' -> '.join(cycle)
                issue = f"Circular dependency: {cycle_str}"
                if issue not in issues:
                    issues.append(issue)

        return issues

    def _find_cycle(self, start):
        """DFS cycle detection from a starting skill.

        Returns:
            list representing the cycle path, or None
        """
        visited = set()
        path = []

        def dfs(node):
            if node in visited:
                # Found cycle — extract cycle path
                if node in path:
                    idx = path.index(node)
                    return path[idx:] + [node]
                return None
            visited.add(node)
            path.append(node)
            skill = self.data['skills'].get(node, {})
            for dep in skill.get('dependencies', []):
                cycle = dfs(dep)
                if cycle:
                    return cycle
            path.pop()
            return None

        return dfs(start)

    def get_dependency_tree(self, skill_name, indent=0, seen=None):
        """Build a recursive dependency tree string.

        Returns:
            list of (indent_level, skill_name) tuples
        """
        self._ensure_skill(skill_name)
        if seen is None:
            seen = set()
        result = [(indent, skill_name)]
        if skill_name in seen:
            result.append((indent + 1, '(circular)'))
            return result
        seen.add(skill_name)
        for dep in self.data['skills'][skill_name].get('dependencies', []):
            if dep in self.data['skills']:
                result.extend(self.get_dependency_tree(dep, indent + 1, seen))
            else:
                result.append((indent + 1, f'{dep} (missing)'))
        return result

    # ── Category & Tags ───────────────────────────────────

    def set_category(self, skill_name, category):
        """Set the category for a skill."""
        self._ensure_skill(skill_name)
        old = self.data['skills'][skill_name].get('category', '')
        self.data['skills'][skill_name]['category'] = category
        self._add_history(skill_name, 'category_changed', f'{old} -> {category}')
        self._rebuild_categories()
        self.save()

    def add_tags(self, skill_name, tags):
        """Add tags to a skill."""
        self._ensure_skill(skill_name)
        current = self.data['skills'][skill_name].get('tags', [])
        added = []
        for tag in tags:
            if tag not in current:
                current.append(tag)
                added.append(tag)
        if added:
            self.data['skills'][skill_name]['tags'] = current
            self._add_history(skill_name, 'tags_added', f'Added: {", ".join(added)}')
            self.save()

    def remove_tags(self, skill_name, tags):
        """Remove tags from a skill."""
        self._ensure_skill(skill_name)
        current = self.data['skills'][skill_name].get('tags', [])
        removed = []
        for tag in tags:
            if tag in current:
                current.remove(tag)
                removed.append(tag)
        if removed:
            self.data['skills'][skill_name]['tags'] = current
            self._add_history(skill_name, 'tags_removed', f'Removed: {", ".join(removed)}')
            self.save()

    # ── Usage Stats ───────────────────────────────────────

    def record_usage(self, skill_name):
        """Record a usage of a skill."""
        self._ensure_skill(skill_name)
        stats = self.data['skills'][skill_name]['stats']
        stats['times_used'] = stats.get('times_used', 0) + 1
        stats['last_used'] = self._now_iso()
        self.save()

    def get_stats(self, skill_name=None):
        """Get usage stats for one or all skills.

        Returns:
            dict of skill_name -> stats if skill_name is None,
            otherwise just the stats dict for that skill
        """
        self._ensure_loaded()
        if skill_name:
            self._ensure_skill(skill_name)
            return self.data['skills'][skill_name]['stats']
        return {
            name: skill['stats']
            for name, skill in self.data['skills'].items()
        }

    def reset_stats(self, skill_name):
        """Reset usage stats for a skill."""
        self._ensure_skill(skill_name)
        self.data['skills'][skill_name]['stats'] = {
            'times_used': 0,
            'last_used': None,
            'created_at': self.data['skills'][skill_name]['stats'].get('created_at', self._now_iso()),
        }
        self._add_history(skill_name, 'stats_reset', 'Usage statistics reset')
        self.save()

    # ── History ────────────────────────────────────────────

    def _add_history(self, skill_name, action, details=''):
        """Add a history entry to a skill (max MAX_HISTORY_ENTRIES)."""
        if skill_name not in self.data['skills']:
            return
        history = self.data['skills'][skill_name].setdefault('history', [])
        history.append({
            'timestamp': self._now_iso(),
            'action': action,
            'details': details,
        })
        # Trim to max entries
        if len(history) > MAX_HISTORY_ENTRIES:
            self.data['skills'][skill_name]['history'] = history[-MAX_HISTORY_ENTRIES:]

    def get_history(self, skill_name=None, limit=20):
        """Get history entries.

        If skill_name is provided, return that skill's history.
        Otherwise, return merged history from all skills, sorted by timestamp.
        """
        self._ensure_loaded()
        if skill_name:
            self._ensure_skill(skill_name)
            entries = self.data['skills'][skill_name].get('history', [])
            return entries[-limit:]

        # Merge all histories
        all_entries = []
        for name, skill in self.data['skills'].items():
            for entry in skill.get('history', []):
                all_entries.append({**entry, 'skill': name})
        all_entries.sort(key=lambda e: e.get('timestamp', ''))
        return all_entries[-limit:]

    # ── Listing ────────────────────────────────────────────

    def list_skills(self, enabled=None, category=None, sort_by='name'):
        """List skills with optional filtering and sorting.

        Args:
            enabled: filter by enabled status (None = all)
            category: filter by category substring
            sort_by: 'name', 'priority', 'version', 'times_used'

        Returns:
            list of (directory_name, skill_data) tuples
        """
        self._ensure_loaded()
        items = list(self.data['skills'].items())

        # Filter
        if enabled is not None:
            items = [(n, s) for n, s in items if s.get('enabled') == enabled]
        if category:
            items = [(n, s) for n, s in items
                     if category.lower() in s.get('category', '').lower()]

        # Sort
        if sort_by == 'priority':
            items.sort(key=lambda x: x[1].get('priority', 5))
        elif sort_by == 'times_used':
            items.sort(key=lambda x: x[1].get('stats', {}).get('times_used', 0), reverse=True)
        elif sort_by == 'version':
            items.sort(key=lambda x: x[1].get('version', '0.0.0'))
        else:
            items.sort(key=lambda x: x[0])

        return items

    # ── Export / Import ────────────────────────────────────

    def export_registry(self):
        """Export registry as JSON string."""
        self._ensure_loaded()
        return json.dumps(self._data, indent=2, ensure_ascii=False)

    def import_registry(self, json_path):
        """Import registry from a JSON file.

        Returns:
            number of skills imported
        """
        data = json.loads(Path(json_path).read_text(encoding='utf-8'))
        if '$schema' not in data or 'skills' not in data:
            raise ValueError("Invalid registry file format")
        count = len(data.get('skills', {}))
        self._data = data
        self.save()
        return count

    # ── Helpers ────────────────────────────────────────────

    def _ensure_skill(self, skill_name):
        """Raise if skill not in registry."""
        self._ensure_loaded()
        if skill_name not in self.data['skills']:
            raise KeyError(f"Skill '{skill_name}' not found in registry")

    def get_skill(self, skill_name):
        """Get a single skill's data."""
        self._ensure_skill(skill_name)
        return self.data['skills'][skill_name]

    def is_empty(self):
        """Check if registry has no skills."""
        self._ensure_loaded()
        return len(self.data.get('skills', {})) == 0
