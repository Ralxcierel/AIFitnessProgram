# AI-use log

The course requires us to disclose which AI tools we used, for which parts, and how we checked the output (proposal, README, and final presentation). Agents add one row at every `/wrapup`. Newest first.

| Date | Who | Tool | What the AI did | How it was checked |
|---|---|---|---|---|
| 2026-11-26 | Ben | Claude Code | Wrote A2 profile storage (SQLite), the A3 profile page, the A4 workout log with personal bests and log page, the A5 profile eval cases and case format, and the C3 input guardrails, with tests | 329 back-end and 48 front-end tests passed; production build succeeded; A2, A3 and A4 checked by hand in a browser with synthetic data; one reviewer agent per step (two for C3), findings fixed with Ben's approval; Ben approved each step. Nothing run against the real model (no API key) |
| 2026-11-24 | Ben | Claude Code | Wrote C2 schemas and TypeScript types, C1 `call_model()`, the C0 Angular shell and README steps, and the A1 profile chat endpoint, with tests | 96 back-end and 6 front-end tests passed; C0 checked in a browser; independent reviewer agents for every step and the phase; Ben approved each step. Not yet run against the real model |
| 2026-11-20 | Jadon | Gemini CLI | Implemented Step B1 calendar parser, synthetic fixtures, and unit test suite | Automated tests (6 passed) and two rounds of independent reviewer agent checks |
| 2026-11-20 | Ben | Claude Code | Wrote the C0 back-end scaffold (FastAPI `/api/health`, `requirements.txt`) and updated `PROGRESS.md` | Ran the server and checked `/api/health` returned ok; one reviewer agent checked the files; Ben approved each step |
| 2026-11-11 | Ben | Claude (claude.ai) | Drafted the design doc, agent rules (`AGENTS.md`), session commands, and progress file | Reviewed and edited by Ben against the course requirements |
