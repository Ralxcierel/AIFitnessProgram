# CLAUDE.md

All project rules live in `AGENTS.md`. Read it fully before doing anything, and follow it exactly.

@AGENTS.md

## Claude Code notes

- Sessions start with `/start` and end with `/wrapup` (defined in `.claude/commands/`).
- For reviews (AGENTS.md section 6), use subagents: one for a section review, three in parallel for a phase review. Reviewer subagents are read-only.
- Auto-accept, auto or bypass-permissions modes: if the session runs in one, ask the human at `/start` whether that is OK. If they approve, it is fine for that person, also in their later sessions; record it once in `PROGRESS.md` → *Decisions log* with their name. The approval covers only that person, never other teammates. If they say no, ask them to switch the mode off. In every mode the `AGENTS.md` rules still apply: plan first, name files, and wait for the human's OK in chat before changes, commits, pushes, API calls and phase changes.
