# Claude Skills Collection

A curated collection of practical Claude Skills for enhancing productivity across Claude.ai, Claude Code, and the Claude API.

This repository combines skills from [awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) with additional custom skills.

## Contents

- [Repository Structure](#repository-structure)
- [What Are Claude Skills?](#what-are-claude-skills)
- [Skills](#skills)
  - [Document Processing](#document-processing)
  - [Development & Code Tools](#development--code-tools)
  - [Data & Analysis](#data--analysis)
  - [Business & Marketing](#business--marketing)
  - [Communication & Writing](#communication--writing)
  - [Creative & Media](#creative--media)
  - [Productivity & Organization](#productivity--organization)
  - [DevOps & Infrastructure](#devops--infrastructure)
  - [LLM Operations](#llm-operations)
- [Getting Started](#getting-started)
- [Creating Skills](#creating-skills)
- [Contributing](#contributing)
- [Resources](#resources)
- [License](#license)

## Repository Structure

- **ルート直下の各フォルダ** — 利用可能なスキル（本ドキュメントの [Skills](#skills) で一覧）。
- [reference/](./reference/) — 外部リポジトリのフォーク・参照用（例: [anthropics/skills](https://github.com/anthropics/skills) のフォーク）。
- [_archive/](./_archive/) — 過去の出力や一時コピーの保管。通常利用には不要。

## What Are Claude Skills?

Claude Skills are customizable workflows that teach Claude how to perform specific tasks according to your unique requirements. Skills enable Claude to execute tasks in a repeatable, standardized manner across all Claude platforms.

## Skills

### Document Processing

- [document-processing](./document-processing/) - PDF、Excel、Wordドキュメントの読み取り・作成・編集・変換。テキスト抽出、フォーム入力、レポート生成、データ変換。
  - [docx](./document-processing/docx/) - Create, edit, analyze Word docs with tracked changes, comments, formatting.
  - [pdf](./document-processing/pdf/) - Extract text, tables, metadata, merge & annotate PDFs.
  - [pptx](./document-processing/pptx/) - Read, generate, and adjust slides, layouts, templates.
  - [xlsx](./document-processing/xlsx/) - Spreadsheet manipulation: formulas, charts, data transformations.

### Development & Code Tools

- [artifacts-builder](./artifacts-builder/) - Suite of tools for creating elaborate, multi-component claude.ai HTML artifacts using modern frontend web technologies (React, Tailwind CSS, shadcn/ui).
- [changelog-generator](./changelog-generator/) - Automatically creates user-facing changelogs from git commits by analyzing history and transforming technical commits into customer-friendly release notes.
- [code-quality](./code-quality/) - コードレビュー、コミットメッセージ生成、リファクタリング提案、テスト作成支援。静的解析、コーディング規約チェック、セキュリティスキャン。
- [git-branch-cleanup](./git-branch-cleanup/) - ローカルGitブランチを分析し、安全にクリーンアップします。マージステータス、古さ、リモート追跡でブランチを分類し、インタラクティブな選択と安全ガードを提供します。
- [mcp-builder](./mcp-builder/) - Guides creation of high-quality MCP (Model Context Protocol) servers for integrating external APIs and services with LLMs using Python or TypeScript.
- [skill-creator](./skill-creator/) - Provides guidance for creating effective Claude Skills that extend capabilities with specialized knowledge, workflows, and tool integrations.
- [webapp-testing](./webapp-testing/) - Tests local web applications using Playwright for verifying frontend functionality, debugging UI behavior, and capturing screenshots.

### Data & Analysis

- [data-analysis](./data-analysis/) - データ分析、可視化、統計処理。Excel、Pandas、SQL、統計解析、データ可視化の支援。

### Business & Marketing

- [brand-guidelines](./brand-guidelines/) - Applies Anthropic's official brand colors and typography to artifacts for consistent visual identity and professional design standards.
- [competitive-ads-extractor](./competitive-ads-extractor/) - Extracts and analyzes competitors' ads from ad libraries to understand messaging and creative approaches that resonate.
- [domain-name-brainstormer](./domain-name-brainstormer/) - Generates creative domain name ideas and checks availability across multiple TLDs including .com, .io, .dev, and .ai extensions.
- [internal-comms](./internal-comms/) - Helps write internal communications including 3P updates, company newsletters, FAQs, status reports, and project updates using company-specific formats.
- [lead-research-assistant](./lead-research-assistant/) - Identifies and qualifies high-quality leads by analyzing your product, searching for target companies, and providing actionable outreach strategies.

### Communication & Writing

- [content-research-writer](./content-research-writer/) - Assists in writing high-quality content by conducting research, adding citations, improving hooks, and providing section-by-section feedback.
- [meeting-insights-analyzer](./meeting-insights-analyzer/) - Analyzes meeting transcripts to uncover behavioral patterns including conflict avoidance, speaking ratios, filler words, and leadership style.

### Creative & Media

- [canvas-design](./canvas-design/) - Creates beautiful visual art in PNG and PDF documents using design philosophy and aesthetic principles for posters, designs, and static pieces.
- [image-enhancer](./image-enhancer/) - Improves image and screenshot quality by enhancing resolution, sharpness, and clarity for professional presentations and documentation.
- [slack-gif-creator](./slack-gif-creator/) - Creates animated GIFs optimized for Slack with validators for size constraints and composable animation primitives.
- [theme-factory](./theme-factory/) - Applies professional font and color themes to artifacts including slides, docs, reports, and HTML landing pages with 10 pre-set themes.
- [video-downloader](./video-downloader/) - Downloads videos from YouTube and other platforms for offline viewing, editing, or archival with support for various formats and quality options.

### Productivity & Organization

- [file-organizer](./file-organizer/) - Intelligently organizes files and folders by understanding context, finding duplicates, and suggesting better organizational structures.
- [invoice-organizer](./invoice-organizer/) - Automatically organizes invoices and receipts for tax preparation by reading files, extracting information, and renaming consistently.
- [raffle-winner-picker](./raffle-winner-picker/) - Randomly selects winners from lists, spreadsheets, or Google Sheets for giveaways and contests with cryptographically secure randomness.

### DevOps & Infrastructure

- [cicd](./cicd/) - CI/CDパイプラインの設計・実装・トラブルシューティング。GitHub Actions、GitLab CI、CircleCI、Jenkinsの設定ファイル作成、ビルド最適化、デプロイ戦略（Blue-Green、Canary、Rolling）の実装。
- [devops](./devops/) - DevOps実践、Kubernetes、モニタリング、本番環境運用、セキュリティ、Terraform。

### LLM Operations

- [llmops](./llmops/) - LLM運用、評価、プロンプトエンジニアリング、RAG（Retrieval-Augmented Generation）の実装と最適化。

### Other

- [developer-growth-analysis](./developer-growth-analysis/) - Analyzes developer growth and productivity metrics.
- [skill-share](./skill-share/) - Share and discover Claude Skills.
- [template-skill](./template-skill/) - Template for creating new Claude Skills.

## Getting Started

### Using Skills in Claude.ai

1. Click the skill icon (🧩) in your chat interface.
2. Add skills from the marketplace or upload custom skills.
3. Claude automatically activates relevant skills based on your task.

### Using Skills in Claude Code

1. Place the skill in `~/.config/claude-code/skills/`:
   ```bash
   mkdir -p ~/.config/claude-code/skills/
   cp -r skill-name ~/.config/claude-code/skills/
   ```

2. Verify skill metadata:
   ```bash
   head ~/.config/claude-code/skills/skill-name/SKILL.md
   ```

3. Start Claude Code:
   ```bash
   claude
   ```

4. The skill loads automatically and activates when relevant.

### Using Skills via API

Use the Claude Skills API to programmatically load and manage skills:

```python
import anthropic

client = anthropic.Anthropic(api_key="your-api-key")

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    skills=["skill-id-here"],
    messages=[{"role": "user", "content": "Your prompt"}]
)
```

See the [Skills API documentation](https://docs.claude.com/en/api/skills-guide) for details.

## Creating Skills

### Skill Structure

Each skill is a folder containing a `SKILL.md` file with YAML frontmatter:

```
skill-name/
├── SKILL.md          # Required: Skill instructions and metadata
├── scripts/          # Optional: Helper scripts
├── templates/        # Optional: Document templates
└── resources/        # Optional: Reference files
```

### Basic Skill Template

```markdown
---
name: my-skill-name
description: A clear description of what this skill does and when to use it.
---

# My Skill Name

Detailed description of the skill's purpose and capabilities.

## When to Use This Skill

- Use case 1
- Use case 2
- Use case 3

## Instructions

[Detailed instructions for Claude on how to execute this skill]

## Examples

[Real-world examples showing the skill in action]
```

### Skill Best Practices

- Focus on specific, repeatable tasks
- Include clear examples and edge cases
- Write instructions for Claude, not end users
- Test across Claude.ai, Claude Code, and API
- Document prerequisites and dependencies
- Include error handling guidance

## Contributing

We welcome contributions! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details on:

- How to submit new skills
- Skill quality standards
- Pull request process
- Code of conduct

### Quick Contribution Steps

1. Ensure your skill is based on a real use case
2. Check for duplicates in existing skills
3. Follow the skill structure template
4. Test your skill across platforms
5. Submit a pull request with clear documentation

## Resources

### Official Documentation

- [Claude Skills Overview](https://www.anthropic.com/news/skills) - Official announcement and features
- [Skills User Guide](https://support.claude.com/en/articles/12512180-using-skills-in-claude) - How to use skills in Claude
- [Creating Custom Skills](https://support.claude.com/en/articles/12512198-creating-custom-skills) - Skill development guide
- [Skills API Documentation](https://docs.claude.com/en/api/skills-guide) - API integration guide
- [Agent Skills Blog Post](https://anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) - Engineering deep dive

### Community Resources

- [Anthropic Skills Repository](https://github.com/anthropics/skills) - Official example skills
- [Claude Community](https://community.anthropic.com) - Discuss skills with other users
- [Skills Marketplace](https://claude.ai/marketplace) - Discover and share skills
- [Awesome Claude Skills](https://github.com/ComposioHQ/awesome-claude-skills) - Curated list of Claude Skills

## License

This repository is licensed under the Apache License 2.0.

Individual skills may have different licenses - please check each skill's folder for specific licensing information.

---

**Note**: Claude Skills work across Claude.ai, Claude Code, and the Claude API. Once you create a skill, it's portable across all platforms, making your workflows consistent everywhere you use Claude.
