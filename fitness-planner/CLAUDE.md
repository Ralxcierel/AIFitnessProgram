# CLAUDE.md

All project rules live in `AGENTS.md`. Read it fully before doing anything, and follow it exactly.

@AGENTS.md

## Claude Code notes

- Sessions start with `/start` and end with `/wrapup` (defined in `.claude/commands/`).
- For reviews (AGENTS.md section 6), use subagents: one for a section review, three in parallel for a phase review. Reviewer subagents are read-only.
- Do not use auto-accept or bypass-permissions modes on this project; every change is approved by the human.
