#!/usr/bin/env python3
"""
Git Branch Cleanup Script (Python版)
ローカルGitブランチを分析し、安全にクリーンアップします
"""

import subprocess
import sys
import re
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class BranchCategory(Enum):
    """ブランチのカテゴリ"""
    MERGED = "merged"
    GONE_REMOTE = "gone_remote"
    AHEAD = "ahead"
    STALE = "stale"
    UNMERGED = "unmerged"


@dataclass
class BranchInfo:
    """ブランチ情報"""
    name: str
    category: BranchCategory
    commit_date: str
    relative_date: str
    subject: str
    upstream: Optional[str] = None
    trackshort: Optional[str] = None
    is_protected: bool = False


class GitBranchCleanup:
    """Gitブランチクリーンアップクラス"""
    
    # 保護ブランチ
    PROTECTED_BRANCHES = {'main', 'master', 'trunk', 'develop', 'development'}
    
    def __init__(self, stale_days: int = 30, dry_run: bool = False):
        self.stale_days = stale_days
        self.dry_run = dry_run
        self.base_branch = self._detect_base_branch()
        self.current_branch = self._get_current_branch()
        
    def _run_git_command(self, cmd: List[str]) -> Tuple[str, int]:
        """Gitコマンドを実行"""
        try:
            result = subprocess.run(
                ['git'] + cmd,
                capture_output=True,
                text=True,
                check=False
            )
            return result.stdout.strip(), result.returncode
        except Exception as e:
            print(f"エラー: Gitコマンド実行失敗: {e}", file=sys.stderr)
            return "", 1
    
    def _detect_base_branch(self) -> str:
        """ベースブランチを検出"""
        output, code = self._run_git_command([
            'symbolic-ref', '--quiet', '--short', 'refs/remotes/origin/HEAD'
        ])
        if code == 0 and output:
            return output.replace('origin/', '')
        return 'main'
    
    def _get_current_branch(self) -> str:
        """現在のブランチを取得"""
        output, code = self._run_git_command(['branch', '--show-current'])
        return output if code == 0 else ''
    
    def _is_protected_branch(self, branch: str) -> bool:
        """保護ブランチかチェック"""
        return branch in self.PROTECTED_BRANCHES or branch == self.current_branch or not branch
    
    def _update_remote_info(self):
        """リモート情報を更新"""
        print("リモート情報を更新中...")
        _, code = self._run_git_command(['fetch', '--prune'])
        if code != 0:
            print("警告: リモートに到達できませんでした。キャッシュされたデータを使用します。\n")
    
    def _get_branch_info(self, branch: str) -> Dict[str, str]:
        """ブランチの詳細情報を取得"""
        info = {}
        
        # コミット日時
        date_output, _ = self._run_git_command([
            'log', '-1', '--format=%ci|%cr', branch
        ])
        if date_output:
            parts = date_output.split('|')
            info['commit_date'] = parts[0] if len(parts) > 0 else ''
            info['relative_date'] = parts[1] if len(parts) > 1 else ''
        else:
            info['commit_date'] = ''
            info['relative_date'] = '不明'
        
        # コミットメッセージ
        subject_output, _ = self._run_git_command([
            'log', '-1', '--format=%s', branch
        ])
        info['subject'] = subject_output or ''
        
        # 上流情報
        upstream_output, _ = self._run_git_command([
            'for-each-ref', f'refs/heads/{branch}',
            '--format=%(upstream:short)|%(upstream:trackshort)'
        ])
        if upstream_output:
            parts = upstream_output.split('|')
            info['upstream'] = parts[0] if len(parts) > 0 else None
            info['trackshort'] = parts[1] if len(parts) > 1 else None
        else:
            info['upstream'] = None
            info['trackshort'] = None
        
        return info
    
    def _is_stale(self, commit_date: str) -> bool:
        """ブランチが古いかチェック"""
        if not commit_date:
            return False
        try:
            commit_dt = datetime.strptime(commit_date.split()[0], '%Y-%m-%d')
            cutoff_dt = datetime.now() - timedelta(days=self.stale_days)
            return commit_dt < cutoff_dt
        except:
            return False
    
    def analyze_branches(self) -> Dict[BranchCategory, List[BranchInfo]]:
        """ブランチを分析して分類"""
        print("## ブランチ分析中...\n")
        
        # リモート情報更新
        self._update_remote_info()
        
        categories = {
            BranchCategory.MERGED: [],
            BranchCategory.GONE_REMOTE: [],
            BranchCategory.AHEAD: [],
            BranchCategory.STALE: [],
            BranchCategory.UNMERGED: []
        }
        
        # すべてのローカルブランチを取得
        all_branches_output, _ = self._run_git_command([
            'for-each-ref', '--sort=-committerdate', 'refs/heads/',
            '--format=%(refname:short)'
        ])
        all_branches = [b.strip() for b in all_branches_output.split('\n') if b.strip()]
        
        # マージ済みブランチ
        merged_output, _ = self._run_git_command([
            'branch', '--merged', self.base_branch
        ])
        merged_branches = set(
            b.strip().lstrip('* ').strip()
            for b in merged_output.split('\n')
            if b.strip()
        )
        
        # 未マージブランチ
        unmerged_output, _ = self._run_git_command([
            'branch', '--no-merged', self.base_branch
        ])
        unmerged_branches = set(
            b.strip().lstrip('* ').strip()
            for b in unmerged_output.split('\n')
            if b.strip()
        )
        
        # リモート削除済みブランチ
        gone_output, _ = self._run_git_command([
            'branch', '-vv'
        ])
        gone_branches = set()
        for line in gone_output.split('\n'):
            if ': gone]' in line:
                match = re.match(r'^\s*\*?\s*(\S+)', line)
                if match:
                    gone_branches.add(match.group(1))
        
        # 各ブランチを分類
        for branch in all_branches:
            if self._is_protected_branch(branch):
                continue
            
            info_dict = self._get_branch_info(branch)
            branch_info = BranchInfo(
                name=branch,
                category=BranchCategory.MERGED,  # デフォルト
                commit_date=info_dict.get('commit_date', ''),
                relative_date=info_dict.get('relative_date', '不明'),
                subject=info_dict.get('subject', ''),
                upstream=info_dict.get('upstream'),
                trackshort=info_dict.get('trackshort'),
                is_protected=self._is_protected_branch(branch)
            )
            
            # 上流より先行しているかチェック
            if branch_info.trackshort and '>' in branch_info.trackshort:
                branch_info.category = BranchCategory.AHEAD
                categories[BranchCategory.AHEAD].append(branch_info)
                continue
            
            # リモート削除済みかチェック
            if branch in gone_branches:
                branch_info.category = BranchCategory.GONE_REMOTE
                categories[BranchCategory.GONE_REMOTE].append(branch_info)
            
            # マージ済みかチェック
            if branch in merged_branches:
                branch_info.category = BranchCategory.MERGED
                categories[BranchCategory.MERGED].append(branch_info)
            elif branch in unmerged_branches:
                branch_info.category = BranchCategory.UNMERGED
                categories[BranchCategory.UNMERGED].append(branch_info)
            
            # 古いブランチかチェック
            if self._is_stale(branch_info.commit_date):
                if branch_info.category not in [BranchCategory.AHEAD]:
                    # 既に他のカテゴリに追加されていない場合のみ
                    if branch_info not in categories[branch_info.category]:
                        categories[BranchCategory.STALE].append(branch_info)
        
        return categories
    
    def display_results(self, categories: Dict[BranchCategory, List[BranchInfo]]):
        """結果を表示"""
        print(f"\nベースブランチ: {self.base_branch}")
        print(f"現在のブランチ: {self.current_branch}\n")
        
        # マージ済み
        print("### 削除可能（マージ済み）")
        if categories[BranchCategory.MERGED]:
            for branch in categories[BranchCategory.MERGED]:
                print(f"  - {branch.name} ({branch.relative_date}) - {branch.subject}")
        else:
            print("  （該当なし）")
        print()
        
        # リモート削除済み
        print("### リモート削除済み")
        if categories[BranchCategory.GONE_REMOTE]:
            for branch in categories[BranchCategory.GONE_REMOTE]:
                print(f"  - {branch.name} ({branch.relative_date}) - {branch.subject}")
        else:
            print("  （該当なし）")
        print()
        
        # 上流より先行
        print("### ⚠️ 上流より先行（削除しないでください）")
        if categories[BranchCategory.AHEAD]:
            for branch in categories[BranchCategory.AHEAD]:
                unpushed = self._count_unpushed_commits(branch.name)
                print(f"  - {branch.name} ({branch.relative_date}) - プッシュされていないコミットが{unpushed}つあります")
        else:
            print("  （該当なし）")
        print()
        
        # 古いブランチ
        print(f"### 古いブランチ（{self.stale_days}日以上）")
        if categories[BranchCategory.STALE]:
            for branch in categories[BranchCategory.STALE]:
                is_merged = "マージ済み" if branch.category == BranchCategory.MERGED else "未マージ"
                print(f"  - {branch.name} ({branch.relative_date}) - {is_merged} - {branch.subject}")
        else:
            print("  （該当なし）")
        print()
        
        # アクティブ（未マージ）
        print("### アクティブ（未マージ）")
        if categories[BranchCategory.UNMERGED]:
            for branch in categories[BranchCategory.UNMERGED]:
                if branch.category != BranchCategory.AHEAD:
                    print(f"  - {branch.name} ({branch.relative_date}) - {branch.subject}")
        else:
            print("  （該当なし）")
        print()
    
    def _count_unpushed_commits(self, branch: str) -> int:
        """プッシュされていないコミット数をカウント"""
        output, _ = self._run_git_command([
            'log', '--oneline', f'@{u}..HEAD'
        ])
        if not output:
            return 0
        return len([l for l in output.split('\n') if l.strip()])
    
    def delete_branches(self, branches: List[str], force: bool = False):
        """ブランチを削除"""
        if not branches:
            print("削除するブランチがありません。")
            return
        
        print("\n以下のブランチが削除されます：")
        for branch in branches:
            print(f"  - {branch}")
        
        if self.dry_run:
            print("\n[ドライラン] 実際には削除されません。")
            return
        
        confirmation = input("\n続行しますか？ (y/N): ")
        if confirmation.lower() != 'y':
            print("キャンセルしました。")
            return
        
        deleted = 0
        failed = 0
        
        for branch in branches:
            cmd = ['branch', '-D' if force else '-d', branch]
            _, code = self._run_git_command(cmd)
            if code == 0:
                print(f"✓ 削除: {branch}")
                deleted += 1
            else:
                print(f"✗ 削除失敗: {branch}")
                failed += 1
        
        print(f"\n削除完了: {deleted}個")
        if failed > 0:
            print(f"削除失敗: {failed}個")
    
    def run(self):
        """メイン処理を実行"""
        # Gitリポジトリかチェック
        _, code = self._run_git_command(['rev-parse', '--git-dir'])
        if code != 0:
            print("エラー: Gitリポジトリではありません。", file=sys.stderr)
            sys.exit(1)
        
        print("=== Gitブランチクリーンアップ ===\n")
        
        # ブランチ分析
        categories = self.analyze_branches()
        
        # 結果表示
        self.display_results(categories)
        
        if self.dry_run:
            print("[ドライラン] プレビューのみ表示")
            return
        
        # 削除オプション
        print("---")
        print("どのカテゴリを削除しますか？")
        print("1. マージ済みのみ（最も安全）")
        print("2. マージ済み + リモート削除済み")
        print("3. 個別に選択")
        print("4. キャンセル")
        
        choice = input("選択 (1-4): ").strip()
        
        if choice == '1':
            branches = [b.name for b in categories[BranchCategory.MERGED]]
            self.delete_branches(branches, force=False)
        elif choice == '2':
            branches = (
                [b.name for b in categories[BranchCategory.MERGED]] +
                [b.name for b in categories[BranchCategory.GONE_REMOTE]]
            )
            self.delete_branches(branches, force=False)
        elif choice == '3':
            selected = input("削除したいブランチ名を入力してください（空白区切り）: ").strip()
            branches = [b.strip() for b in selected.split() if b.strip()]
            self.delete_branches(branches, force=False)
        else:
            print("キャンセルしました。")


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Gitブランチを分析し、安全にクリーンアップします'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='削除を実行せずにプレビューのみ表示'
    )
    parser.add_argument(
        '--stale-days',
        type=int,
        default=30,
        help='古いブランチとみなす日数（デフォルト: 30）'
    )
    
    args = parser.parse_args()
    
    cleanup = GitBranchCleanup(
        stale_days=args.stale_days,
        dry_run=args.dry_run
    )
    cleanup.run()


if __name__ == '__main__':
    main()
