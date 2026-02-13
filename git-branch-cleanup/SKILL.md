---
name: git-branch-cleanup
description: |
  ローカルGitブランチを分析し、安全にクリーンアップします。マージステータス、古さ、リモート追跡でブランチを分類し、
  インタラクティブな選択と安全ガードを提供します。
  ユーザーがブランチのクリーンアップ、古いブランチの削除、Gitブランチの整理をしたい場合、
  またはどのブランチを安全に削除できるか尋ねた場合に使用します。
---

# Gitブランチクリーンアップ

ローカルGitブランチを安全に整理・クリーンアップします。ブランチをマージステータス、古さ、リモート追跡で分類し、安全な削除をガイドします。

## 目次

- クイックスタート
- ワークフロー（ステップ1-5）
- コマンドリファレンス
- ドライランモード
- 安全チェックリスト

## クイックスタート

1. ブランチ分析（ステップ1）
2. 安全レベルで分類（ステップ2）
3. 結果表示と削除対象の選択（ステップ3）
4. 安全ガードで検証（ステップ4）
5. 確認後に削除実行（ステップ5）

## ワークフロー

### ステップ1: ブランチ分析

以下のコマンドで情報を収集します：

```bash
# ベースブランチを決定（自動検出を優先、フォールバックはmain）
BASE_BRANCH="$(
  git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@'
)"
[ -n "$BASE_BRANCH" ] || BASE_BRANCH=main

# すべてのブランチを最終コミット日でリスト
git for-each-ref --sort=-committerdate refs/heads/ \
  --format='%(refname:short)|%(committerdate:relative)|%(upstream:trackshort)|%(contents:subject)'

# マージ済みブランチ（ベースブランチに対して）
git branch --merged "$BASE_BRANCH"

# 未マージブランチ
git branch --no-merged "$BASE_BRANCH"

# 上流が削除されたブランチ（リモートで削除済み）
git branch -vv | grep -F ': gone]' || true

# 上流より先行しているブランチ（プッシュされていないコミットあり）
git for-each-ref refs/heads \
  --format='%(refname:short) %(upstream:trackshort)' \
  | grep '>' || true
```

### ステップ2: 分類

ブランチを安全レベルで分類します：

| カテゴリ | 説明 | 安全性 |
|----------|------|--------|
| **マージ済み（安全）** | 既にベースブランチにマージ済み | 削除可能 |
| **リモート削除済み** | リモートブランチが削除された | レビュー推奨 |
| **古いブランチ** | 30日以上コミットなし | レビュー必要 |
| **上流より先行** | プッシュされていないコミットあり | ⚠️ 削除しない |
| **未マージ** | 作業中のブランチ | 注意して使用 |

> **注意**: 30日は古いブランチ検出の妥当なデフォルトです。チームのスプリントサイクルに応じて調整してください（例：2週間スプリントの場合は14日）。

### ステップ3: 表示形式

```
## ブランチ分析結果

### 削除可能（マージ済み）
  - feature/login (3週間前) - ログイン機能を追加
  - fix/typo (2ヶ月前) - READMEのタイポ修正

### リモート削除済み
  - feature/old-api (1ヶ月前) - リモートブランチが存在しません

### ⚠️ 上流より先行（削除しないでください）
  - feature/wip (1日前) - プッシュされていないコミットが3つあります

### 古いブランチ（30日以上）
  - experiment/cache (2ヶ月前) - 未マージ

### アクティブ（未マージ）
  - feature/new-dashboard (2日前) - 作業中

---
どのカテゴリを削除しますか？
1. マージ済みのみ（最も安全）
2. マージ済み + リモート削除済み
3. 個別に選択
```

### ステップ4: 安全ガード

**これらのブランチは削除しないでください：**
- `main`
- `master`
- `trunk`
- `develop`
- `development`
- 現在チェックアウト中のブランチ

削除前に常に確認：
```
以下のブランチが削除されます：
  - feature/login
  - fix/typo

続行しますか？ (y/N)
```

### ステップ5: 削除実行

```bash
# 確認後
git branch -d <branch-name>  # マージ済みブランチ用
git branch -D <branch-name>  # 強制削除（未マージ）
```

## コマンドリファレンス

```bash
# マージ済みブランチの一括削除（保護ブランチと現在のブランチを除外）
# 注意:
# - bash/zsh互換性のためforループ + caseを使用（zshでの`while IFS= read`の問題を回避）。
# - 正確な名前マッチングのためcase文を使用（grep正規表現のエッジケースを回避）。
# - 現在のブランチを常に除外して誤削除を防止。
BASE_BRANCH="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@')"
[ -n "$BASE_BRANCH" ] || BASE_BRANCH=main
CURRENT_BRANCH="$(git branch --show-current)"
for branch in $(git branch --merged "$BASE_BRANCH" | sed 's/^[* ]*//'); do
  case "$branch" in
    main|master|trunk|develop|development|"$CURRENT_BRANCH"|"") continue ;;
    *) git branch -d "$branch" ;;
  esac
done

# リモート追跡参照の整理（ネットワークアクセスが必要）
# 注意: オフラインまたはリモートに到達できない場合、このステップは失敗する可能性があります。
# 失敗した場合は、このステップをスキップしてください - ブランチ分析はキャッシュされたリモートデータで動作します。
git fetch --prune || echo "警告: リモートに到達できませんでした。キャッシュされたデータを使用します。"

# 最も古いブランチをリスト（30日以上）
git for-each-ref --sort=committerdate refs/heads/ \
  --format='%(committerdate:short) %(refname:short)' | head -20
```

## ドライランモード

削除を実行せずにプレビュー：

```bash
# プレビューのみ
BASE_BRANCH="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@')"
[ -n "$BASE_BRANCH" ] || BASE_BRANCH=main
CURRENT_BRANCH="$(git branch --show-current)"
for branch in $(git branch --merged "$BASE_BRANCH" | sed 's/^[* ]*//'); do
  case "$branch" in
    main|master|trunk|develop|development|"$CURRENT_BRANCH"|"") ;;
    *) echo "$branch" ;;
  esac
done
```

ユーザーが "--dry-run"、"preview"、または "just show me" と言った場合は、ドライランモードをトリガーします。

## 安全チェックリスト

削除前に確認：
- [ ] 現在のブランチではない
- [ ] 保護ブランチではない（ベース/main/master/trunk/develop）
- [ ] プッシュされていないコミットがない（上流より先行していない）
- [ ] ユーザーの確認を取得済み

### クイック安全コマンド

```bash
# 各ローカルブランチの上流との「先行/後続」を表示
git for-each-ref refs/heads \
  --format='%(refname:short)|%(upstream:short)|%(upstream:trackshort)|%(committerdate:relative)|%(contents:subject)' \
  --sort=-committerdate

# 特定のブランチについて、上流より先行していないことを確認（上流が存在する場合）
# （空の出力 => プッシュされていないものなし）
git log --oneline @{u}..HEAD 2>/dev/null || echo "このブランチには上流が設定されていません"
```

## ユーティリティスクリプト

```bash
# インタラクティブなブランチクリーンアップ
bash scripts/git-branch-cleanup.sh

# ドライラン（プレビューのみ）
bash scripts/git-branch-cleanup.sh --dry-run

# Python版（より柔軟な分析）
python scripts/git_branch_cleanup.py
```
