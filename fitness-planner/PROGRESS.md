# PROGRESS.md — Live project status and session handoff

Agents: read this at `/start`, update the step status as you finish each step, and complete every section at `/wrapup` (AGENTS.md section 5). Newest entries go at the top of each log. Do not delete history.

---

## Current phase

**Phase 0 — Setup and contracts** (target Nov 13). Steps C0, C1, C2 must be done before any step that calls the model.

**State on 2026-11-26:** C0 and C2 are done. C1 still waits for its live call (no API key), so Phase 0 is **not** formally complete. With Ben's OK, work went ahead offline: A2, A3, A4 done; C3 built (B must wire two checks); A5 cases written (Phase 3, not run). Nothing has been tested against the real model yet. B2, B3, B4, C4, C5 not started. The demo video is due **Dec 2**.

## Next up

**If the API key is available — Workstream C, step C1 live call:** create `fitness-planner/.env` (human only), fill in the key and prices, then make one approved live call through `call_model()` with a synthetic persona and check that it adds one line to `logs/usage.jsonl` with tokens, latency and cost. If OpenAI rejects the `default` values in `schemas.py`, stop and ask. Then try the A1 profile chat in the browser at `/profile` with a synthetic persona (ask first; about 3–5 calls).

**If there is still no key — Workstream B, step B2 or C4 offline:** B2 (plan endpoint) can be built with a fake `call_model` in tests, like `backend/tests/test_profile.py` does, and should wire in `guardrails.ics_is_too_large()`, `guardrails.health_flags()` and the 400 refusal format (DESIGN.md §5). C4 (eval harness) can be built to read `eval/cases/profile.json` using `eval/cases/README.md`, tested with a fake model. B is furthest behind, so B2 first if a B person is available.

*(Setup on a new machine: `pip install -r requirements.txt` in `backend/.venv` and `npm ci` in `frontend/`.)*

## Status board

Status: Not started · In progress · Done · Blocked

| ID | Step | Phase | Owner | Status | Last session |
|---|---|---|---|---|---|
| C0 | Scaffold (FastAPI health, Angular shell, run instructions) | 0 | Ben | Done (health status shown in the browser) | 2026-11-24 Ben |
| C1 | `call_model()` + usage log + dev cache | 0 | Ben | In progress (code + offline tests done; live call deferred, no API key on Ben's machine) | 2026-11-24 Ben |
| C2 | Finalize `schemas.py` + `api.types.ts` | 0 | Ben | Done (`schemas.py` and `api.types.ts` match) | 2026-11-24 Ben |
| A1 | Profile chat endpoint | 1 | Ben | In progress (code + offline tests; prompt not yet tried on the real model) | 2026-11-24 Ben |
| B1 | `.ics` parser + free slots + fixtures | 1 | Jadon | Done | 2026-11-20 |
| B2 | Plan generation endpoint | 1 | Ben | Done offline (`POST /api/calendar`, `POST /api/plan`, `GET /api/plan/current` in `plan.py`; 32 offline tests with a fake model, 361 back-end tests pass; prompt not yet tried on the real model — no API key) | 2026-11-26 Ben |
| A3 | Angular profile page (minimal → full) | 1–2 | Ben | Done (`/profile`: chat panel + editable card; 26 front-end tests pass; save, reload and the "assistant unavailable" chat error seen in the browser; a real chat reply not yet seen — no API key) | 2026-11-26 Ben |
| B4 | Angular calendar upload + plan view (minimal → full) | 1–2 | Ben | Done offline (`/plan` page: upload, free times by day, "Make my plan", week view with notes and sessions; 80 front-end tests pass, build OK; upload, re-upload and the "Finish your profile first" refusal seen in the browser with a synthetic calendar; a real plan not yet seen — no API key) | 2026-11-26 Ben |
| A2 | Profile storage (SQLite) | 2 | Ben | Done (`db.py`, GET/PUT `/api/profile`, chat reads and saves the profile; 111 offline tests pass; synthetic profile survived a manual server restart; chat link not yet tried on the real model) | 2026-11-26 Ben |
| A4 | Workout log + personal bests | 2 | Ben | Done (`workout_log.py`, log table in `db.py`, `/log` page; 145 back-end and 45 front-end tests pass; entries, a tie, name matching and a no-weight entry seen in the browser before the review fixes) | 2026-11-26 Ben |
| B3 | Plan checks + exercise allow-list + retry | 2 | Ben | Done offline (`plan_checks.py`, 45-exercise `app/data/exercises.json`, one retry in `plan.py`; 392 back-end tests pass; not yet tried on the real model — no API key) | 2026-11-26 Ben |
| C3 | Input guardrails + wiring | 2 | Ben | Done (wired into the profile chat; B2 wired the `.ics` size check, health flags, the 400 refusal format and an injection screen of saved-profile text before the plan call) | 2026-11-26 Ben |
| A5 | 8 profile test cases | 3 | Ben | In progress (9 cases in `eval/cases/profile.json`, format in `eval/cases/README.md`, offline file check passes; not run or scored — needs the C4 harness and an API key) | 2026-11-26 Ben |
| B5 | 8 plan test cases + fixtures | 3 | Ben | In progress (8 cases in `eval/cases/plan.json` on the existing fixtures, format and scoring incl. baseline in `eval/cases/README.md`, offline file check passes; not run or scored — needs the C4 harness and an API key) | 2026-11-26 Ben |
| C4 | Eval harness + safety and injection cases | 3 | Ben | Done offline (`eval/run_eval.py` + `eval/metrics.py` run and score all 25 cases: 9 profile, 8 plan, 5 safety, 3 injection; reports to `eval/results/`; 558 back-end tests pass with a fake model; never run live — no API key, so no report exists yet) | 2026-11-26 Ben |
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
- [x] **C4:** Build `run_eval.py` / `metrics.py` to read `eval/cases/profile.json` — done in C4a (2026-11-26), offline only.
- [x] **B5:** Reuse the case-file layout in `eval/cases/README.md` for `plan.json` — done 2026-11-26 (same file layout; plan rules in the README's "Plan case format" section).
- [x] **C4:** Build the plan side of `run_eval.py` / `metrics.py` — done in C4a (2026-11-26); the baseline scoring rules wait for C5.
- [x] **C4b:** 5 safety + 3 injection cases — done 2026-11-26 (offline). Includes the injection hidden in a saved profile field (`injection-03`), answering the C3/C4 question below for the plan endpoint.
- [ ] **C5 / team:** DESIGN.md §10's injection criteria are covered as: "refusal flag set" by `injection-01` (`refused: true`) and `injection-03` (400 refusal; `/api/plan` has no flag); "no prompt leaked" by `reply_excludes` in `injection-01/02`. `injection-02` is a polite leak attempt that the pattern screen does not catch — expect it to show the screen's limits in the results. Mention this in the presentation.
- [ ] **A / C:** The profile chat itself does not screen the *saved* profile it sends to the model (only `/api/plan` does). Add an eval case or a screen if the team wants it covered.
- [ ] **C5:** Add a `baseline` mode to `run_eval.py` (naive single prompt, same cases, scoring rules in `eval/cases/README.md`). Reports are named `<time>-<mode>`.
- [ ] **Ben:** The first live eval: run 2–3 cases with `--only ... --live` once the key exists (about 3–5 calls), then the rest (25 cases: about 31 calls, at most 38).
- [ ] **Ben (B5):** §8 bans calorie and weight-loss targets, but nothing checks it. Add a `notes_exclude` rule (e.g. "calorie") to the plan case format and use it on `plan-06` ("lose fat")?
- [ ] **B:** The too-few-free-days refusal says "only 1 days" (plural bug in `plan.py`). `plan-08` matches "free time on only 1", so fixing it will not break the case.
- [ ] **Team / C5:** There are 9 profile cases, not 8 (a "vague answers" case was added), so the eval has 25 cases instead of DESIGN.md §10's 24. Update §10's table when C5 writes up the results.
- [ ] **A / B3:** Workout log exercise names are free text (1–100 characters). Once B3's `exercises.json` exists, should the log page suggest or require names from it?
- [x] **C3:** The profile page blocks chat messages over 2,000 characters in the browser only — the back end now enforces it too (C3, 2026-11-26).
- [ ] **C3 / C4:** The profile chat sends the saved profile (user-written text, e.g. `name`, `health_notes`) to the model as a system message, marked "JSON data, not instructions". Add an injection test case that puts an attack in a saved profile field.
- [x] **B:** Free-slot defaults — minimum 45 min, between 06:00 and 22:00 local time — confirmed by Jadon.
- [ ] **A / B:** `backend/app/schemas.py` is now the shared contract for later steps; `calendar_ics.py` imports its `FreeSlot` (Ben approved 2026-11-24).
- [ ] **B:** Possible bug from reading the code (not run): `find_free_slots` does not expand repeating events (`RRULE`), so later occurrences may look free.
- [x] **B / C:** Refusal format for `/api/plan` — settled in C3 (2026-11-26): HTTP 400 `{"error": "Request refused", "detail": <message>}`, see DESIGN.md §5.
- [x] **B (B2 / B4):** (done in B2, 2026-11-26) Use `guardrails.ics_is_too_large()` in `POST /api/calendar` (200 KB), `guardrails.health_flags()` on the profile's injuries and health notes to add a "check with a doctor or physical therapist" note in the plan, and the 400 refusal format above. C3 stays In progress until this is wired.
- [ ] **C3 / C4:** The injection screen is a pattern list (no model call). Its known limits are listed in `backend/tests/test_guardrails.py` (ATTACKS / BENIGN). The final round of regex fixes was self-checked with tests only, not by a separate reviewer. Saved-profile text sent with `PUT /api/profile` is not screened.
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
- [x] **B:** `Session` times from the model may carry a time zone while `FreeSlot` times do not — answered 2026-11-26 (Ben): all local with no time zone; `plan.py` converts any model time zone to local.
- [x] **Ben:** Is it OK that this session ran in auto mode? — answered 2026-11-26: new per-person rule in `CLAUDE.md` / `GEMINI.md`; Ben approved auto mode for himself.
- [ ] **Jadon, Ethan:** If your agent runs in an auto / YOLO mode, it will now ask you once whether that is OK (`CLAUDE.md` / `GEMINI.md`). Your answer is recorded under your name in the Decisions log.
- [ ] **Ben:** Commits from Ben's machine show the author as "MainPC". Change the git name?
- [x] **B / C:** Wire `POST /api/calendar` endpoint — done in B2 (2026-11-26), in `plan.py`.
- [ ] **Ben (B2):** If `POST /api/plan` gets a `week_of` that differs from the uploaded calendar's first day, it refuses with 400 ("Upload a calendar for that week"). Agent choice — confirm or change.
- [ ] **B / C:** The 200 KB `.ics` limit is checked after the upload is received (fine for the local demo).
- [ ] **Ben (B3):** Add a minimum session length (e.g. 15 minutes)? Today a 1-minute session passes the checks.
- [ ] **Ben / C5 (B3):** Label the retry call `"plan_retry"` in the usage log so C5 can count retries? Both calls use `"plan"` today.
- [ ] **A:** `frontend/src/app/core/error-text.ts` now holds the shared `errorText()` helper (B4). The profile and log pages still have their own copies; switch them over when convenient.
- [ ] **A / B (contract):** `api.types.ts` now has `CalendarResponse`; keep it in step with `CalendarResponse` in `backend/app/plan.py`.
- [ ] **Ben (B2/B4):** "Finish your profile first. Still missing: height_cm, weight_kg, …" shows raw field names on the plan page. Use friendly names ("height", "weight")? Small change in `plan.py`.
- [ ] **B (B3):** Optional: add a few no-equipment cardio exercises to `exercises.json` (e.g. "March in place").
- [ ] **A / team:** Do we attempt the voice-input stretch goal? Decide by the end of Phase 2.
- [x] **C:** (both added; `httpx` approved by Ben 2026-11-24) Add `pytest` and `httpx` to `backend/requirements.txt` so `/api/health` (and later steps) get automated tests with FastAPI's `TestClient`? Needs approval (new dependencies).
- [ ] **Team:** Does the instructor need an addendum to the proposal for the scope change (meal photos and diet tracking deferred)?

## Decisions log

| Date | Decision | Decided by |
|---|---|---|
| 2026-11-26 | C4b: safety/injection cases carry `"kind": "profile" \| "plan"` and reuse that kind's rules; new rules `reply_excludes` (reply and returned profile text must not contain prompt phrases) and `model_calls_max` (from the usage log); leak markers = headings and distinctive sentences of the profile prompt; `injection-02` scored on no-leak only; main metric for both groups = case-pass rate; listing shows expected and worst-case model calls; new fixture `full.ics` | Ben |
| 2026-11-26 | Switch to workstream C for C4; split C4 into C4a (harness + scoring for profile/plan cases) and C4b (safety + injection cases) | Ben |
| 2026-11-26 | C4a: `run_eval.py` lists cases and max model calls by default and calls nothing; `--live` needed; `--only` / `--group`; dev cache on by default (`--no-cache` for the graded run); `.env` via python-dotenv, never printed; one timestamped JSON + Markdown report per run in `eval/results/` (committed; scores, counts and usage only); a failing case does not stop the run | Ben |
| 2026-11-26 | Start Phase 3 with B5 (before C4), offline, although Phases 1–2 are not yet tried on the real model | Ben |
| 2026-11-26 | B5: 8 plan cases on the existing fixtures for the week of 2026-11-23; main metric = constraint-pass rate with the harness re-running `check_plan()` on slots it computes itself (times made local first, a crash = not passed); extra checks: status, session count, notes keywords, refusal keywords, excluded exercise words (judgement checks count in the check-pass rate only); baseline: status/detail not scored, `plan-08` passes only with zero sessions | Ben |
| 2026-11-26 | Contract change: add `CalendarResponse` (`{free_slots: FreeSlot[]}`) to `frontend/src/app/core/api.types.ts`, mirroring `CalendarResponse` in `backend/app/plan.py` | Ben |
| 2026-11-26 | B4: `/plan` page between Profile and Log in the menu; shared `core/error-text.ts` used by the plan page only; a new upload clears the plan on screen; files over 200 KB refused in the browser too; one always-present status line for screen readers; tested with fake HTTP plus a browser check | Ben |
| 2026-11-26 | B3: exercise names match ignoring case and extra spaces, and the listed activity type must match; fewer free days than `workout_days` → 400 refusal before any model call; a second failed plan → 502 `{"error": "The plan did not pass the checks", "detail": problems}`, nothing saved; the retry sends the finished failed plan plus the problem list (at most 2 calls); session length = end − start | Ben |
| 2026-11-26 | Work on B2 this session (B furthest behind); keep git name "Anozin" | Ben |
| 2026-11-26 | B2: add `python-multipart` (`>=0.0.9,<1`, bounds chosen by agent) for the `.ics` form upload | Ben |
| 2026-11-26 | B2: all plan and slot times are local with no time zone; a time zone from the model is converted to local and dropped (answers the B open question on time zones) | Ben |
| 2026-11-26 | B2: no calendar, no free time, missing core profile fields, or injection-like saved-profile text → 400 refusal, no model call; `health_flags()` on injuries + health notes adds a fixed doctor/PT note in Python and is passed to the model | Ben |
| 2026-11-26 | B2 review fixes: profile data sent as a user message (not system); `name` and diet fields not sent to the model; a new calendar upload clears the current plan; upload handler made synchronous | Ben |
| 2026-11-26 | Rule change (`CLAUDE.md`, `GEMINI.md`, `HOW_TO_START.md`): auto / auto-accept / YOLO modes are allowed per person once that person approves it when asked at `/start`; recorded here by name; AGENTS.md approvals in chat still apply | Ben |
| 2026-11-26 | Auto mode approved for Ben's own sessions | Ben |
| 2026-11-26 | Switch from workstream A to C for step C3 this session | Ben |
| 2026-11-26 | C3: pattern-list injection screen only (no classification model call); user messages get the full check, assistant messages only chat control tokens; flagged chat → 200 refusal with the saved profile, no model call; limits 2,000 characters per message and 40 messages per chat → 422; model replies cut to 2,000 characters; the profile page stops sending refused exchanges and sends at most the newest 40 messages | Ben |
| 2026-11-26 | C3: `.ics` size check (200 KB) and health red-flag finder built for B to wire in later | Ben |
| 2026-11-26 | Contract change (DESIGN.md §5): a refused `/api/plan` request returns 400 `{"error": "Request refused", "detail": message}` | Ben |
| 2026-11-26 | C3: after two reviews, the last regex fixes are self-checked with tests, no third reviewer | Ben |
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

### 2026-11-26 — Ben — Claude Code — Workstreams A and C

- **Goal this session:** continue workstream A; then, with Ben's OK, start A5 early and switch to C3.
- **Steps worked on:** A2 (Done), A3 (Done), A4 (Done), A5 (In progress: cases written, not run), C3 (In progress: built and wired into the profile chat; B must wire the `.ics` and health checks).
- **What was done:**
  - A2: SQLite profile storage in `db.py`; `GET`/`PUT /api/profile`; the chat reads and saves the profile.
  - A3: `/profile` page with a chat panel and an editable profile card; nav links.
  - A4: workout log and personal bests (`workout_log.py`) and the `/log` page.
  - A5: 9 synthetic profile eval cases, a case-format README for C4/B5, and an offline file check.
  - C3: `guardrails.py` (length limits, injection screen, `.ics` size check, health red flags), wired into the profile chat; `/api/plan` refusal format added to DESIGN.md §5.
- **Files created / modified / deleted:**
  - created: `backend/app/db.py`, `backend/app/workout_log.py`, `backend/app/guardrails.py`, `backend/tests/test_storage.py`, `backend/tests/test_workout_log.py`, `backend/tests/test_eval_cases.py`, `backend/tests/test_guardrails.py`, `frontend/src/app/profile/` (6 files), `frontend/src/app/log/` (6 files), `eval/cases/profile.json`, `eval/cases/README.md`
  - modified: `backend/app/profile.py`, `backend/app/main.py`, `backend/tests/test_profile.py`, `frontend/src/app/app.html`, `app.ts`, `app.routes.ts`, `app.spec.ts`, `frontend/src/app/core/api.types.ts` (contract: `ChatMessage`, `ProfileChatRequest`), `docs/DESIGN.md` (§5), `PROGRESS.md`, `docs/AI_USE.md`
  - deleted: none committed (test databases and build output made during checks were removed)
- **Tests:** `pytest` in `backend/`: 329 passed. `npm test -- --watch=false` in `frontend/`: 48 passed. Production build succeeded. All offline; **no OpenAI calls were made**. A2, A3, A4 checked by hand in the browser with synthetic data.
- **Reviews:** one section reviewer each for A2, A3, A4, A5; C3 had a review and a re-review (two high findings, both fixed). Fixes were made with Ben's approval. The last C3 regex fixes were self-checked with tests only (Ben's choice).
- **Unfinished or left as-is:** A1 prompt and C1 live call still untested (no key); A5 cases not run (needs C4 and key); C3 checks for B not yet wired; saved-profile text from `PUT /api/profile` is not screened; a small `errorText()` helper is repeated in the profile and log pages.
- **Pushed:** yes (A2, A3, A4, A5 pushed during the session; C3 and wrap-up pushed at the end)
- **Notes for the next person:** `pip install -r requirements.txt` and `npm ci` were needed on this machine. This session again ran in auto mode while each step was still approved by Ben in chat (see the open question about auto mode). Commits now show the git name "Anozin".

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
