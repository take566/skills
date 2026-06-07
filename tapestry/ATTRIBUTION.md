# Attribution

Vendored into the Claude Skills Collection from an upstream source. The upstream
repository is a **suite of thinking/knowledge skills** (there is no single skill
named `tapestry`); it is vendored intact as a bundled suite and excluded from the
flat skill installer discovery (see `scripts/skill_discovery.py` `EXCLUDED_DIRS`),
mirroring the `gws-cli-skills` / `self-improving-agent` treatment.

- **Source**: https://github.com/michalparkola/tapestry-skills-for-claude-code/tree/80e1dc56df74d1cb849ad649c7ead9756e7929bb
- **Upstream commit**: `80e1dc56df74d1cb849ad649c7ead9756e7929bb`
- **License**: MIT (see `LICENSE`)
- **Original author**: Michal Parkola

Sub-skills: `article-extractor`, `learn-this`, `scrum-sage`, `session-log`,
`ship-learn-next`, `unblock-action`, `youtube-transcript`. No functional changes
were made.
