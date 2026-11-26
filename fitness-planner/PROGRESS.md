# PROGRESS.md — Live project status and session handoff

Agents: read this at `/start`, update the step status as you finish each step, and complete every section at `/wrapup` (AGENTS.md section 5). Newest entries go at the top of each log. Do not delete history.

---

## Current phase

**Phase 0 — Setup and contracts** (target Nov 13). Steps C0, C1, C2 must be done before any step that calls the model.

**State on 2026-11-24:** C0 and C2 are done. C1 waits for its live call (no API key), so Phase 0 is **not** complete. Ben allowed A1 (Phase 1) to start with offline tests only.

## Next up

**Workstream C, step C1 — live call:** create `fitness-planner/.env` (human only), fill in the key and prices, then make one approved live call through `call_model()` with a synthetic persona and check that it adds one line to `logs/usage.jsonl` with tokens, latency and cost. If OpenAI rejects the `default` values in `schemas.py`, stop and ask. Then try the A1 prompt with a synthetic persona (ask first). Do not close Phase 0 until the live call works.

*(Whoever starts first should take workstream C, unless the team agrees otherwise.)*

## Status board

Status: Not started · In progress · Done · Blocked

| ID | Step | Phase | Owner | Status | Last session |
|---|---|---|---|---|---|
| C0 | Scaffold (FastAPI health, Angular shell, run instructions) | 0 | Ben | Done (health status shown in the browser) | 2026-11-24 Ben |
| C1 | `call_model()` + usage log + dev cache | 0 | Ben | In progress (code + offline tests done; live call deferred, no API key on Ben's machine) | 2026-11-24 Ben |
| C2 | Finalize `schemas.py` + `api.types.ts` | 0 | Ben | Done (`schemas.py` and `api.types.ts` match) | 2026-11-24 Ben |
| A1 | Profile chat endpoint | 1 | Ben | In progress (code + offline tests; prompt not yet tried on the real model) | 2026-11-24 Ben |
| B1 | `.ics` parser + free slots + fixtures | 1 | Jadon | Done | 2026-11-20 |
| B2 | Plan generation endpoint | 1 | ? | Not started | — |
| A3 | Angular profile page (minimal → full) | 1–2 | Ben | Done (`/profile`: chat panel + editable card; 26 front-end tests pass; save, reload and the "assistant unavailable" chat error seen in the browser; a real chat reply not yet seen — no API key) | 2026-11-26 Ben |
| B4 | Angular calendar upload + plan view (minimal → full) | 1–2 | ? | Not started | — |
| A2 | Profile storage (SQLite) | 2 | Ben | Done (`db.py`, GET/PUT `/api/profile`, chat reads and saves the profile; 111 offline tests pass; synthetic profile survived a manual server restart; chat link not yet tried on the real model) | 2026-11-26 Ben |
| A4 | Workout log + personal bests | 2 | Ben | Done (`workout_log.py`, log table in `db.py`, `/log` page; 145 back-end and 45 front-end tests pass; entries, a tie, name matching and a no-weight entry seen in the browser before the review fixes) | 2026-11-26 Ben |
| B3 | Plan checks + exercise allow-list + retry | 2 | ? | Not started | — |
| C3 | Input guardrails + wiring | 2 | ? | Not started | — |
| A5 | 8 profile test cases | 3 | Ben | In progress (9 cases in `eval/cases/profile.json`, format in `eval/cases/README.md`, offline file check passes; not run or scored — needs the C4 harness and an API key) | 2026-11-26 Ben |
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
- [x] **Team:** Single local user with no login for the demo (DESIGN.md §2) — confirmed by Ben 2026-11-26.
- [ ] **B / C:** `api.types.ts` now also has `ChatMessage` and `ProfileChatRequest` (the body of `POST /api/profile/chat`; they mirror `ChatMessage` and `ProfileChatRequest` in `backend/app/profile.py`, not `schemas.py`). Ben approved 2026-11-26. Keep them in step if the chat request changes.
- [ ] **C4:** Build `run_eval.py` / `metrics.py` to read `eval/cases/profile.json` using the format and scoring rules in `eval/cases/README.md` (written in A5). Each case needs its own throwaway database (patch `db.DB_PATH`).
- [ ] **B5:** Reuse the case-file layout in `eval/cases/README.md` for `plan.json`, so C4 has one format to read.
- [ ] **Team / C5:** There are 9 profile cases, not 8 (a "vague answers" case was added), so the eval has 25 cases instead of DESIGN.md §10's 24. Update §10's table when C5 writes up the results.
- [ ] **A / B3:** Workout log exercise names are free text (1–100 characters). Once B3's `exercises.json` exists, should the log page suggest or require names from it?
- [ ] **C3:** The profile page blocks chat messages over 2,000 characters in the browser only; the back-end length cap is still C3's job.
- [ ] **C3 / C4:** The profile chat sends the saved profile (user-written text, e.g. `name`, `health_notes`) to the model as a system message, marked "JSON data, not instructions". Add an injection test case that puts an attack in a saved profile field.
- [x] **B:** Free-slot defaults — minimum 45 min, between 06:00 and 22:00 local time — confirmed by Jadon.
- [ ] **A / B:** `backend/app/schemas.py` is now the shared contract for later steps; `calendar_ics.py` imports its `FreeSlot` (Ben approved 2026-11-24).
- [ ] **B:** Possible bug from reading the code (not run): `find_free_slots` does not expand repeating events (`RRULE`), so later occurrences may look free.
- [ ] **B / C:** Refusal format for `/api/plan`: `WeeklyPlan` has no `refused` or message field. Settle in C3.
- [ ] **A / B:** Use `call_model(feature, messages, response_model)` from `backend/app/llm.py`; catch `LLMError`.
- [ ] **Ben:** `call_model()` sends `store=False` so OpenAI does not keep responses (profiles can hold health data). Agent choice, not yet confirmed.
- [ ] **C:** Strict output mode may reject the `default` values in `schemas.py`; untested until the first live call.
- [ ] **Ben / C:** Replace `httpx` with `httpx2`? FastAPI's current test client prefers `httpx2`.
- [x] **Ben / C:** (answered 2026-11-24: add `python-dotenv`; README run command comes with C0) Nothing loads `.env` yet. Add `python-dotenv` (new package; lets uvicorn use `--env-file`) or document a manual shell step? Blocks the live C1 call.
- [ ] **Ben / C:** `call_model()` uses the SDK defaults: 2 transport retries and a 10-minute timeout. Set shorter limits?
- [ ] **A / B:** `frontend/src/app/core/api.types.ts` is now the shared TypeScript contract; use it for all API types.
- [ ] **Ben:** When the key arrives, create `.env` and make the deferred C1 live call (ask again before calling). Until then nothing has been tested against the real API.
- [ ] **A / C:** Chat refusals use `refused: true` with the message in `reply` (DESIGN.md §5). C3 must set this; the A1 prompt always asks for `refused: false`.
- [ ] **B / C:** `main.py` turns `LLMError` into 502, invalid requests into 422, and other HTTP errors (400 unreadable body, 404, 405) into `{error, detail}` with their own status.
- [ ] **C5:** In `logs/usage.jsonl`, tokens and `cost_usd` can be `null`; cached calls log 0. `summarize_usage.py` must handle both.
- [x] **A2:** Pass the stored profile to the chat (DESIGN.md §7.1) — done 2026-11-26 (offline tests only).
- [ ] **Ben:** Phase 0 review findings not fixed yet (all low; need an OK because they touch files outside the approved lists or need a choice):
  - `.gitignore`: ignore `.env*` except `.env.example` (today `.env.bak` or `.env.production` could be committed); widen the Claude and Gemini ignore lists to match.
  - Dev cache (`eval/cache/`) will hold profile data: add it to the Claude and Gemini ignore lists and tell users to set `LLM_CACHE=0` with real data.
  - `llm.py`: if `logs/usage.jsonl` cannot be written, the paid result is lost. Raise `LLMError`, or warn and return the result? (It also reaches the user as a plain-text 500.)
  - `llm.py`: output cut off mid-JSON is reported as "did not match" instead of "incomplete".
  - `docs/DESIGN.md`: §6 still says "Draft"; §9 and §11 do not mention the cache key with schema, or `null` tokens and cost.
- [ ] **B:** `Session` times from the model may carry a time zone while `FreeSlot` times do not; comparing them fails. Agree before B2/B3.
- [ ] **Ben:** Is it OK that this session ran in auto mode? `CLAUDE.md` says not to use auto-accept modes here. Asked several times, not answered.
- [ ] **Ben:** Commits from Ben's machine show the author as "MainPC". Change the git name?
- [ ] **B / C:** Wire `POST /api/calendar` endpoint once FastAPI scaffold in C0 is merged.
- [ ] **A / team:** Do we attempt the voice-input stretch goal? Decide by the end of Phase 2.
- [x] **C:** (both added; `httpx` approved by Ben 2026-11-24) Add `pytest` and `httpx` to `backend/requirements.txt` so `/api/health` (and later steps) get automated tests with FastAPI's `TestClient`? Needs approval (new dependencies).
- [ ] **Team:** Does the instructor need an addendum to the proposal for the scope change (meal photos and diet tracking deferred)?

## Decisions log

| Date | Decision | Decided by |
|---|---|---|
| 2026-11-26 | Start A5 (Phase 3) now, before Phase 2 is complete (B3, B4, C3 still open; no API key); write the cases now, run and score them once C4 and the key exist | Ben |
| 2026-11-26 | A5 cases: mixed matching rules (exact for experience and whole numbers; ±tolerance for cm/kg; keyword groups for text and lists; "empty" for never-given fields; exact `missing_fields`); format documented in `eval/cases/README.md`; a 9th "vague answers" case added | Ben |
| 2026-11-26 | A4: personal best = heaviest `weight_kg` per exercise, earliest date on a tie; entries without weight have no best; names grouped ignoring case and spacing, shown as first logged; bests sorted by name; log listed newest first | Ben |
| 2026-11-26 | A4: `POST /api/log` trims the exercise name (1–100 characters), limits sets and reps to 1–1000 and weight to 0–1000 kg (no Infinity/NaN), allows future dates, and ignores a sent `id`; checks live in `workout_log.py`, `schemas.py` unchanged; no edit or delete endpoints | Ben |
| 2026-11-26 | A3: profile page at `/profile` with a chat panel and an editable card; chat history kept on the page only; list fields edited as comma-separated text; plain styling; Home · Profile links (needed a small `app.ts` change) | Ben |
| 2026-11-26 | A3: chat waits while the card has unsaved edits ("Save your edits before chatting"), and Save waits while a chat reply is pending; Save is off if the profile could not be loaded; a failed chat message goes back into the input box | Ben |
| 2026-11-26 | Contract change: add `ChatMessage` and `ProfileChatRequest` to `frontend/src/app/core/api.types.ts` | Ben |
| 2026-11-26 | A2: one local user, no login; the profile is stored as JSON text in one SQLite row in `backend/app/db.py` (name from DESIGN.md §3); `GET /api/profile` returns an empty profile (200) when none is saved; an unreadable saved profile is treated as empty, with a warning in the server log that holds no profile data | Ben |
| 2026-11-26 | A2: the chat sends the saved profile to the model and saves the returned profile; a refusal or failed model call saves nothing, and a refusal returns the saved profile | Ben |
| 2026-11-24 | Start A1 (Phase 1) with offline tests only while C1's live call is deferred; Phase 0 is not complete | Ben |
| 2026-11-24 | A1: chat history only until A2; Python computes `missing_fields` from 6 core fields; model failure returns 502; bad requests on all endpoints return 422 `{error, detail}` without echoing input | Ben |
| 2026-11-24 | API key not available now; keep working on the assumption that it will be in a future session. C1's live call is deferred, not waived | Ben |
| 2026-11-24 | C0: Angular 22 app from the official generator (routing, plain CSS, no server-side rendering, default Vitest runner); home page only; dev proxy `/api` → `127.0.0.1:8000` | Ben |
| 2026-11-24 | `api.types.ts` mirrors `schemas.py`; dates are ISO strings; one `api.service.ts` for now, A and B may add their own | Ben |
| 2026-11-24 | Add `python-dotenv` (`>=1,<2`, bounds chosen by agent); start the back end from `backend/` with `uvicorn --env-file ../.env` | Ben |
| 2026-11-24 | C1: `call_model(feature, messages, response_model)`; cache in `eval/cache/` keyed on model + prompt + schema; invalid output or refusal logs `valid: false` and raises `LLMError`; blank prices log `cost_usd: null`; cached calls log cost 0 | Ben |
| 2026-11-24 | Profile chat refusals use `ProfileChatResponse` (`refused: true`, message in `reply`); DESIGN.md §5 corrected, schemas unchanged | Ben |
| 2026-11-24 | Path: finish Phase 0, then A1 | Ben |
| 2026-11-24 | Schemas: `schemas.py` uses the DESIGN.md §6 draft as written; `calendar_ics.py` imports the shared `FreeSlot` | Ben |
| 2026-11-24 | Add `openai` (`>=3,<4`) and `httpx` (`>=0.28,<1`) to `backend/requirements.txt` | Ben (packages; version bounds chosen by agent) |
| 2026-11-20 | Free-slot defaults: minimum 45 min, between 06:00 and 22:00 local time | Jadon |
| 2026-11-20 | `backend/` and `frontend/` live inside `fitness-planner/` | Ben |
| 2026-11-20 | Add `uvicorn` to `backend/requirements.txt` (server that runs FastAPI); versions bounded: `fastapi>=0.115,<1`, `uvicorn>=0.30,<1`, `pydantic>=2,<3` | Ben |
| 2026-11-20 | Create the front end with the official Angular generator (`npx @angular/cli@latest new`) | Ben |
| 2026-11-20 | Assume `gpt-6-luna` is the only text model for now (no small-vs-large baseline unless that changes) | Ben |
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

### 2026-11-24 — Ben — Claude Code — Workstreams C and A

- **Goal this session:** continue workstream A. A1 was blocked by Phase 0, so Ben chose "Phase 0, then A1".
- **Steps worked on:** C0 (Done), C2 (Done), C1 (In progress: live call deferred), A1 (In progress: offline only).
- **What was done:**
  - C2: shared Pydantic models and the matching `api.types.ts`; `calendar_ics.py` uses the shared `FreeSlot`.
  - C1: `call_model()` with structured output, usage log and dev cache.
  - C0: Angular 22 shell, health page, dev proxy, README setup and run steps. Seen in a browser with the back end running and stopped.
  - A1: `POST /api/profile/chat`; all handled errors use `{error, detail}`.
- **Files created / modified / deleted:**
  - created: `backend/app/schemas.py`, `backend/app/llm.py`, `backend/app/profile.py`, `backend/tests/test_schemas.py`, `backend/tests/test_llm.py`, `backend/tests/test_profile.py`, `frontend/` (Angular project)
  - modified: `backend/app/main.py`, `backend/app/calendar_ics.py`, `backend/requirements.txt`, `docs/DESIGN.md` (§5), `README.md`, `PROGRESS.md`, `docs/AI_USE.md`
  - deleted: none
- **Tests:** `pytest` in `backend/`: 96 passed. `npm test -- --watch=false` in `frontend/`: 6 passed. Production build succeeded. All offline; **no OpenAI calls were made**.
- **Reviews:** C2 three rounds, C1 two, C0 one, A1 two; bugs found were fixed except one optional C2 test idea (check optional field names). Phase 0 review: three reviewers, no high or medium defects in correctness, conformance or security; low findings are in *Open questions* and have not been fixed or re-reviewed.
- **Unfinished or left as-is:** C1 live call; the A1 prompt is untested on the real model; starting the back end with a real `.env` and the Mac/Linux commands are untested; low review findings above.
- **Pushed:** yes
- **Notes for the next person:** run `pip install -r requirements.txt` in `backend/` and `npm ci` in `frontend/` first (new packages). Phases 0 and 1 are past their target dates; the video is due Dec 2.

### 2026-11-20 — Jadon — Gemini CLI — Workstream B

- **Goal this session:** Implement Step B1 (.ics calendar parser, synthetic test fixtures, and free slot calculation).
- **Steps worked on:** B1 (Done).
- **What was done:**
  - Implemented `.ics` file parsing in `calendar_ics.py` extracting busy windows and calculating free slots (>= 45 min, 06:00 to 22:00 window).
  - Created 3 synthetic test calendar fixtures (`empty.ics`, `normal.ics`, `packed.ics`) with generic placeholder events.
  - Added 6 unit tests in `test_calendar_ics.py` testing standard, busy, edge cases, and RFC 5545 non-inclusive all-day events.
  - Initialized `requirements.txt` with `icalendar`, `pytest`, `pydantic`.
- **Files created / modified / deleted:**
  - created: `fitness-planner/backend/requirements.txt`, `fitness-planner/backend/app/calendar_ics.py`, `fitness-planner/backend/tests/test_calendar_ics.py`, `fitness-planner/eval/fixtures/empty.ics`, `fitness-planner/eval/fixtures/normal.ics`, `fitness-planner/eval/fixtures/packed.ics`
  - modified: `fitness-planner/PROGRESS.md`, `fitness-planner/docs/AI_USE.md`
  - deleted: none
- **Tests:** `python3 -m pytest fitness-planner/backend/tests/test_calendar_ics.py` — 6 passed in 1.86s.
- **Reviews:** Section review performed by reviewer agent; caught all-day event non-inclusive DTEND bug. Fixed and re-checked by fresh reviewer agent — final verdict PASS.
- **Unfinished or left as-is:** `POST /api/calendar` route wiring awaits C0 FastAPI scaffold.
- **Pushed:** yes.
- **Notes for the next person:** Step B1 parser and fixtures are ready in `fitness-planner/backend/app/calendar_ics.py`. Next up is step C0 (scaffolding FastAPI and Angular).

### 2026-11-20 — Ben — Claude Code — Workstream C

- **Goal this session:** start Phase 0 with step C0 (Ben first asked for A, but A1 needs Phase 0 done first, so switched to C0).
- **Steps worked on:** C0 — In progress (back-end slice done).
- **What was done:**
  - Pulled Jadon's test commit (one line in the top-level `README.md`).
  - Created the FastAPI app with `GET /api/health` → `{"status": "ok"}` and `backend/requirements.txt` (fastapi, uvicorn, pydantic v2, bounded versions).
  - Made a local virtual environment `backend/.venv` (gitignored) and installed the requirements.
  - Ran the server with `uvicorn app.main:app --port 8000` from `backend/`: `/api/health` returned `{"status":"ok"}`, an unknown path returned 404.
- **Files created / modified / deleted:**
  - created: `backend/requirements.txt`, `backend/app/__init__.py`, `backend/app/main.py`
  - modified: `PROGRESS.md`, `docs/AI_USE.md`
  - deleted: none committed (a stray local `uv.log` server log in the repo's top folder was deleted with Ben's OK; it was never committed)
- **Tests:** not run — no test suite yet (pytest not approved; see *Open questions*). Manual server check passed.
- **Reviews:** section review by one reviewer agent — no serious findings; added version bounds to `requirements.txt` as it suggested. Its other notes (dev proxy for Angular, Python version in README, a health test) are in *Next up* / *Open questions*.
- **Unfinished or left as-is:** C0 front end (Angular app, API service, proxy) and README run instructions — see *Next up*.
- **Pushed:** yes
- **Notes for the next person:** on Ben's Windows machine `python` opens the Microsoft Store; use `py -m venv .venv`, then `.venv\Scripts\python -m pip install -r requirements.txt` and `.venv\Scripts\python -m uvicorn app.main:app --port 8000` from `backend/`. Angular CLI is not installed globally — use `npx @angular/cli@latest`.

### 2026-11-11 — Ben — Claude (claude.ai) — Planning

- **Goal this session:** design the project and the agent workflow.
- **What was done:** wrote `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `docs/DESIGN.md`, `PROGRESS.md`, `/start` and `/wrapup` commands for both tools, onboarding and handoff docs.
- **Files created:** all files in the initial commit.
- **Tests:** none (no code yet).
- **Pushed:** to be done by Ben in the initial commit.
- **Notes for the next person:** start with step C0. Read `docs/HOW_TO_START.md` if this is your first session.
