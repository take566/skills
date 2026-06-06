# Attribution

Vendored into the Claude Skills Collection from an upstream source. This is a full
Claude Code **plugin** (skills + agents + hooks + commands + templates), vendored
intact as a bundled skill suite. It is excluded from the flat skill installer
discovery (see `scripts/skill_discovery.py` `EXCLUDED_DIRS`); install the whole
plugin directory rather than a single `SKILL.md`.

- **Source**: https://github.com/alirezarezvani/claude-skills/tree/fcd4fa1b203a9a0dc44d2482af21adfb53b7a727/engineering-team/self-improving-agent
- **Upstream commit**: `fcd4fa1b203a9a0dc44d2482af21adfb53b7a727`
- **License**: MIT (see `LICENSE`)
- **Original author**: Alireza Rezvani

Sub-skills: `self-improving-agent` (orchestrator), `extract`, `promote`,
`remember`, `review`, `status`. No functional changes were made.
