# GEMINI.md

All project rules live in `AGENTS.md`. Read it fully before doing anything, and follow it exactly. If the import below does not load it, open `AGENTS.md` yourself before your first reply.

@./AGENTS.md

## Gemini CLI notes

- Sessions start with `/start` and end with `/wrapup` (defined in `.gemini/commands/`).
- For reviews (AGENTS.md section 6): if you cannot start separate reviewer agents, do a separate self-review pass and tell the human it was a self-review.
- YOLO / auto-approve mode: if the session runs in it, ask the human at `/start` whether that is OK. If they approve, it is fine for that person, also in their later sessions; record it once in `PROGRESS.md` → *Decisions log* with their name. The approval covers only that person, never other teammates. If they say no, ask them to switch the mode off. In every mode the `AGENTS.md` rules still apply: plan first, name files, and wait for the human's OK in chat before changes, commits, pushes, API calls and phase changes.
- If the human is using Gemini in a web browser instead of the CLI, follow `docs/WEB_CHAT_HANDOFF.md`.
