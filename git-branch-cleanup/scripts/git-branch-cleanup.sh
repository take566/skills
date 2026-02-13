#!/bin/bash
#
# Git Branch Cleanup Script
# ローカルGitブランチを分析し、安全にクリーンアップします
#

set -euo pipefail

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 設定
STALE_DAYS=${STALE_DAYS:-30}
DRY_RUN=false

# 引数解析
if [[ "$*" =~ --dry-run ]] || [[ "$*" =~ preview ]] || [[ "$*" =~ "just show me" ]]; then
    DRY_RUN=true
fi

# ベースブランチを決定
detect_base_branch() {
    BASE_BRANCH=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@' || echo "")
    [ -n "$BASE_BRANCH" ] || BASE_BRANCH=main
    echo "$BASE_BRANCH"
}

# 現在のブランチを取得
get_current_branch() {
    git branch --show-current
}

# 保護ブランチかチェック
is_protected_branch() {
    local branch=$1
    case "$branch" in
        main|master|trunk|develop|development|"")
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# ブランチ分析
analyze_branches() {
    local base_branch=$1
    local current_branch=$2
    
    echo -e "${BLUE}## ブランチ分析中...${NC}\n"
    
    # リモート情報を更新（オプション）
    echo "リモート情報を更新中..."
    git fetch --prune 2>/dev/null || echo -e "${YELLOW}警告: リモートに到達できませんでした。キャッシュされたデータを使用します。${NC}\n"
    
    # マージ済みブランチ
    echo -e "${GREEN}### 削除可能（マージ済み）${NC}"
    local merged_branches=()
    while IFS= read -r branch; do
        branch=$(echo "$branch" | sed 's/^[* ]*//')
        if [[ -n "$branch" ]] && ! is_protected_branch "$branch" && [[ "$branch" != "$current_branch" ]]; then
            local commit_date=$(git log -1 --format='%cr' "$branch" 2>/dev/null || echo "不明")
            local subject=$(git log -1 --format='%s' "$branch" 2>/dev/null || echo "")
            echo "  - $branch ($commit_date) - $subject"
            merged_branches+=("$branch")
        fi
    done < <(git branch --merged "$base_branch" 2>/dev/null || echo "")
    
    if [[ ${#merged_branches[@]} -eq 0 ]]; then
        echo "  （該当なし）"
    fi
    echo ""
    
    # リモート削除済みブランチ
    echo -e "${YELLOW}### リモート削除済み${NC}"
    local gone_branches=()
    while IFS= read -r line; do
        local branch=$(echo "$line" | awk '{print $1}')
        if [[ -n "$branch" ]] && ! is_protected_branch "$branch" && [[ "$branch" != "$current_branch" ]]; then
            local commit_date=$(git log -1 --format='%cr' "$branch" 2>/dev/null || echo "不明")
            local subject=$(git log -1 --format='%s' "$branch" 2>/dev/null || echo "")
            echo "  - $branch ($commit_date) - $subject"
            gone_branches+=("$branch")
        fi
    done < <(git branch -vv 2>/dev/null | grep -F ': gone]' || true)
    
    if [[ ${#gone_branches[@]} -eq 0 ]]; then
        echo "  （該当なし）"
    fi
    echo ""
    
    # 上流より先行しているブランチ（削除しない）
    echo -e "${RED}### ⚠️ 上流より先行（削除しないでください）${NC}"
    local ahead_branches=()
    while IFS= read -r line; do
        local branch=$(echo "$line" | awk '{print $1}')
        if [[ -n "$branch" ]]; then
            local unpushed=$(git log --oneline @{u}..HEAD 2>/dev/null | wc -l || echo "0")
            if [[ "$unpushed" -gt 0 ]]; then
                local commit_date=$(git log -1 --format='%cr' "$branch" 2>/dev/null || echo "不明")
                local subject=$(git log -1 --format='%s' "$branch" 2>/dev/null || echo "")
                echo "  - $branch ($commit_date) - プッシュされていないコミットが${unpushed}つあります"
                ahead_branches+=("$branch")
            fi
        fi
    done < <(git for-each-ref refs/heads --format='%(refname:short) %(upstream:trackshort)' 2>/dev/null | grep '>' || true)
    
    if [[ ${#ahead_branches[@]} -eq 0 ]]; then
        echo "  （該当なし）"
    fi
    echo ""
    
    # 古いブランチ（30日以上）
    echo -e "${YELLOW}### 古いブランチ（${STALE_DAYS}日以上）${NC}"
    local stale_branches=()
    local cutoff_date=$(date -d "${STALE_DAYS} days ago" +%Y-%m-%d 2>/dev/null || date -v-${STALE_DAYS}d +%Y-%m-%d 2>/dev/null || echo "")
    
    while IFS= read -r line; do
        local commit_date=$(echo "$line" | awk '{print $1}')
        local branch=$(echo "$line" | awk '{print $2}')
        if [[ -n "$branch" ]] && ! is_protected_branch "$branch" && [[ "$branch" != "$current_branch" ]]; then
            local relative_date=$(git log -1 --format='%cr' "$branch" 2>/dev/null || echo "不明")
            local subject=$(git log -1 --format='%s' "$branch" 2>/dev/null || echo "")
            local is_merged=$(git branch --merged "$base_branch" | grep -q "^[* ]*${branch}$" && echo "マージ済み" || echo "未マージ")
            echo "  - $branch ($relative_date) - $is_merged - $subject"
            stale_branches+=("$branch")
        fi
    done < <(git for-each-ref --sort=committerdate refs/heads/ --format='%(committerdate:short) %(refname:short)' 2>/dev/null | head -20)
    
    if [[ ${#stale_branches[@]} -eq 0 ]]; then
        echo "  （該当なし）"
    fi
    echo ""
    
    # アクティブな未マージブランチ
    echo -e "${BLUE}### アクティブ（未マージ）${NC}"
    local unmerged_branches=()
    while IFS= read -r branch; do
        branch=$(echo "$branch" | sed 's/^[* ]*//')
        if [[ -n "$branch" ]] && [[ "$branch" != "$current_branch" ]]; then
            local commit_date=$(git log -1 --format='%cr' "$branch" 2>/dev/null || echo "不明")
            local subject=$(git log -1 --format='%s' "$branch" 2>/dev/null || echo "")
            echo "  - $branch ($commit_date) - $subject"
            unmerged_branches+=("$branch")
        fi
    done < <(git branch --no-merged "$base_branch" 2>/dev/null | grep -v "^[* ]*${current_branch}$" || echo "")
    
    if [[ ${#unmerged_branches[@]} -eq 0 ]]; then
        echo "  （該当なし）"
    fi
    echo ""
    
    # 結果を返す（配列を返すのは難しいので、グローバル変数を使用）
    MERGED_BRANCHES=("${merged_branches[@]}")
    GONE_BRANCHES=("${gone_branches[@]}")
    AHEAD_BRANCHES=("${ahead_branches[@]}")
    STALE_BRANCHES=("${stale_branches[@]}")
    UNMERGED_BRANCHES=("${unmerged_branches[@]}")
}

# ブランチ削除
delete_branches() {
    local branches=("$@")
    local force=$1
    shift
    local branches_to_delete=("$@")
    
    if [[ ${#branches_to_delete[@]} -eq 0 ]]; then
        echo -e "${YELLOW}削除するブランチがありません。${NC}"
        return
    fi
    
    echo -e "\n${YELLOW}以下のブランチが削除されます：${NC}"
    for branch in "${branches_to_delete[@]}"; do
        echo "  - $branch"
    done
    
    if [[ "$DRY_RUN" == true ]]; then
        echo -e "\n${BLUE}[ドライラン] 実際には削除されません。${NC}"
        return
    fi
    
    echo -e "\n続行しますか？ (y/N)"
    read -r confirmation
    if [[ ! "$confirmation" =~ ^[Yy]$ ]]; then
        echo "キャンセルしました。"
        return
    fi
    
    local deleted=0
    local failed=0
    
    for branch in "${branches_to_delete[@]}"; do
        if [[ "$force" == "true" ]]; then
            if git branch -D "$branch" 2>/dev/null; then
                echo -e "${GREEN}✓ 削除: $branch${NC}"
                ((deleted++))
            else
                echo -e "${RED}✗ 削除失敗: $branch${NC}"
                ((failed++))
            fi
        else
            if git branch -d "$branch" 2>/dev/null; then
                echo -e "${GREEN}✓ 削除: $branch${NC}"
                ((deleted++))
            else
                echo -e "${YELLOW}強制削除が必要かもしれません: $branch${NC}"
                ((failed++))
            fi
        fi
    done
    
    echo -e "\n${GREEN}削除完了: ${deleted}個${NC}"
    if [[ $failed -gt 0 ]]; then
        echo -e "${YELLOW}削除失敗: ${failed}個${NC}"
    fi
}

# メイン処理
main() {
    # Gitリポジトリかチェック
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo -e "${RED}エラー: Gitリポジトリではありません。${NC}"
        exit 1
    fi
    
    local base_branch=$(detect_base_branch)
    local current_branch=$(get_current_branch)
    
    echo -e "${BLUE}=== Gitブランチクリーンアップ ===${NC}\n"
    echo "ベースブランチ: $base_branch"
    echo "現在のブランチ: $current_branch"
    echo ""
    
    # ブランチ分析
    analyze_branches "$base_branch" "$current_branch"
    
    # 削除オプション表示
    echo -e "${BLUE}---${NC}"
    echo "どのカテゴリを削除しますか？"
    echo "1. マージ済みのみ（最も安全）"
    echo "2. マージ済み + リモート削除済み"
    echo "3. 個別に選択"
    echo "4. キャンセル"
    echo -n "選択 (1-4): "
    
    if [[ "$DRY_RUN" == true ]]; then
        echo "[ドライラン] プレビューのみ表示"
        return
    fi
    
    read -r choice
    
    case "$choice" in
        1)
            delete_branches false "${MERGED_BRANCHES[@]}"
            ;;
        2)
            local combined=("${MERGED_BRANCHES[@]}" "${GONE_BRANCHES[@]}")
            delete_branches false "${combined[@]}"
            ;;
        3)
            echo "削除したいブランチ名を入力してください（空白区切り、Enterで確定）:"
            read -r -a selected_branches
            delete_branches false "${selected_branches[@]}"
            ;;
        4|*)
            echo "キャンセルしました。"
            ;;
    esac
}

main "$@"
