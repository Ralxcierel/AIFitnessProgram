# PROGRESS.md — Live project status and session handoff

Agents: read this at `/start`, update the step status as you finish each step, and complete every section at `/wrapup` (AGENTS.md section 5). Newest entries go at the top of each log. Do not delete history.

---

## Current phase

**Phase 0 — Setup and contracts** (target Nov 13). Steps C0, C1, C2 must be done before any step that calls the model.

## Next up

**Workstream C, step C0:** create the scaffold — FastAPI app with `/api/health`, Angular shell with routing and an API service, `backend/requirements.txt`, and run instructions in `README.md`. Done when both run locally and the browser shows the health status from the back end. See `docs/DESIGN.md` §3 and §9.

*(Whoever starts first should take workstream C, unless the team agrees otherwise.)*

## Status board

Status: Not started · In progress · Done · Blocked

| ID | Step | Phase | Owner | Status | Last session |
|---|---|---|---|---|---|
| C0 | Scaffold (FastAPI health, Angular shell, run instructions) | 0 | ? | Not started | — |
| C1 | `call_model()` + usage log + dev cache | 0 | ? | Not started | — |
| C2 | Finalize `schemas.py` + `api.types.ts` | 0 | ? | Not started | — |
| A1 | Profile chat endpoint | 1 | ? | Not started | — |
| B1 | `.ics` parser + free slots + fixtures | 1 | ? | Not started | — |
| B2 | Plan generation endpoint | 1 | ? | Not started | — |
| A3 | Angular profile page (minimal → full) | 1–2 | ? | Not started | — |
| B4 | Angular calendar upload + plan view (minimal → full) | 1–2 | ? | Not started | — |
| A2 | Profile storage (SQLite) | 2 | ? | Not started | — |
| A4 | Workout log + personal bests | 2 | ? | Not started | — |
| B3 | Plan checks + exercise allow-list + retry | 2 | ? | Not started | — |
| C3 | Input guardrails + wiring | 2 | ? | Not started | — |
| A5 | 8 profile test cases | 3 | ? | Not started | — |
| B5 | 8 plan test cases + fixtures | 3 | ? | Not started | — |
| C4 | Eval harness + safety and injection cases | 3 | ? | Not started | — |
| C5 | Baseline run, usage summary, README sections | 3 | ? | Not started | — |
| — | Phase 4: polish, README, demo video | 4 | all | Not started | — |

## Open questions

Each is addressed to a person or workstream. Ask at `/start` when that person or workstream is up. Move answered ones to the *Decisions log*.

- [ ] **Team:** Who owns workstream A, B, and C? (Fill the Owner column.)
- [ ] **Team:** Team name and GitHub repo link (needed for the README title).
- [ ] **C:** Exact name of the transcription model listed as "got-transcribe" in the notebook (only needed if we do voice input).
- [ ] **C / team:** Does the course notebook offer a smaller text model besides `gpt-6-luna`? If yes, add a small-vs-large baseline (DESIGN.md §10).
- [ ] **C:** Per-token prices for `gpt-6-luna` (for `.env` → `PRICE_INPUT_PER_1M`, `PRICE_OUTPUT_PER_1M`).
- [ ] **Team:** Single local user with no login for the demo (DESIGN.md §2) — confirm.
- [ ] **B:** Free-slot defaults — minimum 45 min, between 06:00 and 22:00 local time — confirm.
- [ ] **A / team:** Do we attempt the voice-input stretch goal? Decide by the end of Phase 2.
- [ ] **Team:** Does the instructor need an addendum to the proposal for the scope change (meal photos and diet tracking deferred)?

## Decisions log

| Date | Decision | Decided by |
|---|---|---|
| 2026-11-11 | Product is a **web app**: Angular front end + FastAPI back end + SQLite | Ben (for team) |
| 2026-11-11 | Model: `gpt-6-luna` from the course notebook for all text tasks | Ben (for team) |
| 2026-11-11 | Demo scope: profile chat, `.ics` → weekly plan, workout log; meal photos, calorie tracking, open Q&A deferred | Ben (for team) |
| 2026-11-11 | App may collect basic personal, medical, and dietary info; tests, fixtures, and demo video use synthetic personas only | Ben (for team) |
| 2026-11-11 | Three feature workstreams: A Profile, B Plan, C Platform | Ben (for team) |
| 2026-11-11 | Relay workflow: one person at a time, all on `main`; agent runs git and asks before every push | Ben (for team) |
| 2026-11-11 | Reviews: 1 reviewer agent per completed step; 3 reviewer agents only at phase ends or named large chunks | Ben (for team) |
| 2026-11-11 | Shared rules in `AGENTS.md`; Claude Code and Gemini CLI both use `/start` and `/wrapup` | Ben (for team) |

## Session log

Newest first. Copy the template for each new session.

<!--
### YYYY-MM-DD — <name> — <tool: Claude Code / Gemini CLI / Gemini web> — Workstream <A/B/C>

- **Goal this session:**
- **Steps worked on:** <IDs and final status>
- **What was done:** <2–5 bullets>
- **Files created / modified / deleted:**
  - created: …
  - modified: …
  - deleted: …
- **Tests:** <command run and result, or "not run — reason">
- **Reviews:** <section / phase review, findings, what was fixed>
- **Unfinished or left as-is:** <anything half-done, and where>
- **Pushed:** yes / no (reason)
- **Notes for the next person:**
-->

### 2026-11-11 — Ben — Claude (claude.ai) — Planning

- **Goal this session:** design the project and the agent workflow.
- **What was done:** wrote `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `docs/DESIGN.md`, `PROGRESS.md`, `/start` and `/wrapup` commands for both tools, onboarding and handoff docs.
- **Files created:** all files in the initial commit.
- **Tests:** none (no code yet).
- **Pushed:** to be done by Ben in the initial commit.
- **Notes for the next person:** start with step C0. Read `docs/HOW_TO_START.md` if this is your first session.
