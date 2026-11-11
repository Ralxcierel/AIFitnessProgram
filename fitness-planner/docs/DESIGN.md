# Fitness Planner — Design and Contracts

This is the agents' source of truth for *what* to build. `AGENTS.md` says *how* to work. If you change the team's planning doc, update this file too (it is a shared contract — see AGENTS.md section 7).

---

## 1. Product

A web app for beginners who find fitness information overwhelming. The user:

1. chats with an assistant that builds their profile (body stats, goals, schedule needs, basic health and dietary information);
2. uploads a calendar file (`.ics`);
3. gets a one-week workout plan placed in their real free time;
4. logs workouts and sees personal bests.

**What the LLM does (real work, as the course requires):** extracts a structured profile from free-text chat, and plans workouts into free calendar slots as schema-validated JSON.

## 2. Scope for the Dec 2 demo

| In scope | Out of scope (mention as future work) |
|---|---|
| Profile chat → validated profile | Meal photo / nutrition-label analysis |
| `.ics` upload → free slots | Daily calorie tracking |
| Weekly plan generation + rule checks | Open-ended fitness Q&A |
| Workout log + personal bests | Multi-user accounts and login |
| Guardrails, usage log, evaluation | Mobile app |
| *Stretch:* voice input to the profile chat (`gpt-4o-mini-transcribe`) | |

**Single local user for the demo** (no login). One profile per running app. *(Open item — see §13.)*

## 3. Architecture

```
 Browser (Angular web app)
   │  REST / JSON
   ▼
 FastAPI back end (Python)
   ├─ guardrails.py      input checks (length, injection, health red flags)
   ├─ profile.py         profile chat  ──┐
   ├─ calendar_ics.py    .ics → free slots (plain Python, no LLM)
   ├─ plan.py            plan generation ─┤──► llm.py: call_model() ──► OpenAI API (gpt-6-luna)
   ├─ plan_checks.py     output rules (plain Python)       │
   ├─ workout_log.py     log + personal bests              └──► logs/usage.jsonl
   └─ db.py              SQLite (backend/data/app.db)
```

Only two features call the model (profile chat, plan generation), both through `call_model()`. Everything deterministic is plain Python so it is cheap and unit-testable. This is a **fixed workflow, not an agent** — a choice to explain in the final presentation.

### Repository layout

```
backend/
  app/
    main.py            FastAPI app + routers
    llm.py             call_model(), usage log, dev cache      [contract]
    schemas.py         Pydantic models                         [contract]
    guardrails.py
    profile.py
    calendar_ics.py
    plan.py
    plan_checks.py
    workout_log.py
    db.py
    data/exercises.json  exercise allow-list
  data/                SQLite file (gitignored)
  tests/
  requirements.txt
frontend/
  src/app/
    core/api.types.ts  TS mirror of schemas                    [contract]
    core/api.service.ts
    profile/           profile chat page + summary card
    plan/              calendar upload + weekly plan view
    log/               workout log + personal bests
eval/
  cases/               profile.json, plan.json, safety.json, injection.json
  fixtures/            synthetic personas and .ics files
  run_eval.py
  metrics.py
  results/             saved eval reports (committed)
logs/usage.jsonl       usage log (committed; contains no prompts or personal data)
docs/
```

## 4. Data handling

- **Team decision:** the app may collect basic personal, medical, and dietary information (height, weight, injuries, conditions, allergies, dietary preferences) to personalize plans.
- **Course rules still apply to what we create and show:** all test fixtures, eval cases, screenshots, and the demo video use **synthetic personas**. No real teammate data in the repo, the eval, or the video.
- Only free time slots reach the model — never calendar event titles or descriptions.
- `logs/usage.jsonl` holds metadata only (tokens, latency, cost) — never prompt text or profile data.
- The app runs locally or behind a temporary share link; it is never left publicly deployed.

## 5. API endpoints [contract]

| Method | Path | Body | Returns | Workstream |
|---|---|---|---|---|
| GET | `/api/health` | — | `{"status": "ok"}` | C |
| POST | `/api/profile/chat` | `{"messages": [{"role": "user"\|"assistant", "content": str}]}` | `ProfileChatResponse` | A |
| GET | `/api/profile` | — | `UserProfile` | A |
| PUT | `/api/profile` | `UserProfile` | `UserProfile` | A |
| POST | `/api/calendar` | multipart `.ics` file | `{"free_slots": [FreeSlot]}` | B |
| POST | `/api/plan` | `{"week_of": date}` (optional) | `WeeklyPlan` | B |
| GET | `/api/plan/current` | — | `WeeklyPlan` or 404 | B |
| POST | `/api/log` | `LogEntry` | `LogEntry` | A |
| GET | `/api/log` | — | `[LogEntry]` | A |
| GET | `/api/log/bests` | — | `[PersonalBest]` | A |

Errors return `{"error": str, "detail": str | null}` with a fitting HTTP status. A guardrail refusal returns 200 with `{"refused": true, "message": str}` inside the normal response so the UI can show it.

## 6. Schemas [contract]

Draft — finalized in step C2, then mirrored in `api.types.ts`.

```python
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field

class UserProfile(BaseModel):
    name: str | None = None
    height_cm: float | None = Field(None, gt=100, lt=250)
    weight_kg: float | None = Field(None, gt=30, lt=300)
    experience: Literal["beginner", "intermediate", "advanced"] | None = None
    goals: list[str] = []
    workout_days: int | None = Field(None, ge=1, le=6)
    session_minutes: int | None = Field(None, ge=15, le=120)
    split_preference: str | None = None
    equipment: list[str] = []
    injuries: list[str] = []            # basic, user-stated
    health_notes: str | None = None     # basic, user-stated
    dietary_preferences: list[str] = []
    dietary_restrictions: list[str] = [] # incl. allergies

class ProfileChatResponse(BaseModel):
    reply: str
    profile: UserProfile
    missing_fields: list[str]
    refused: bool = False

class FreeSlot(BaseModel):
    start: datetime
    end: datetime

class Exercise(BaseModel):
    name: str                            # must be in exercises.json
    activity_type: Literal["strength", "cardio", "mobility"]
    sets: int = Field(ge=1, le=6)
    reps: int = Field(ge=1, le=30)

class Session(BaseModel):
    start: datetime
    end: datetime
    focus: str
    exercises: list[Exercise] = Field(min_length=1)

class WeeklyPlan(BaseModel):
    week_of: date
    sessions: list[Session]
    notes: list[str] = []                # e.g. "check with a physical therapist about your knee"

class LogEntry(BaseModel):
    id: int | None = None
    date: date
    exercise: str
    sets: int = Field(ge=1)
    reps: int = Field(ge=1)
    weight_kg: float | None = Field(None, ge=0)

class PersonalBest(BaseModel):
    exercise: str
    best_weight_kg: float
    date: date
```

Personal bests are computed in Python from `LogEntry` rows — the model never produces past performance.

## 7. LLM tasks

**Model:** `gpt-6-luna` for both tasks (from `.env` → `OPENAI_MODEL`).

### 7.1 Profile chat (workstream A)
- Input: chat history + current stored profile.
- Output: `ProfileChatResponse` via structured output.
- Fields the user has not given stay `null` / empty. The model does not guess them; `missing_fields` lists them and `reply` asks for one or two at a time.
- Converts units the user gives (ft/in, lb) into cm/kg.

### 7.2 Plan generation (workstream B)
- Input: `UserProfile` + list of `FreeSlot` for the next 7 days.
- Output: `WeeklyPlan` via structured output.
- Then `plan_checks.py` runs (§8). On failure: one retry with the error messages in the prompt; on a second failure, return a clear error to the UI.

### 7.3 Calendar preprocessing (no LLM, workstream B)
- Parse with the `icalendar` library; expand the next 7 days from today.
- Free slot = gap of at least 45 minutes between 06:00 and 22:00 local time (defaults — confirm with the human).
- Return only start/end times.

## 8. Guardrails

**Input (before any model call), `guardrails.py`:**
- Length caps: chat message ≤ 2,000 characters; `.ics` file ≤ 200 KB.
- Prompt-injection screen: a pattern list ("ignore previous", "system prompt", role tags, etc.) plus an optional cheap classification call. Flagged input → fixed refusal message, no model call for the main task.
- Health red flags (serious injury, chest pain, pregnancy, heart condition, eating-disorder signals): store what the user said, but the plan adds a "check with a doctor or physical therapist" note, avoids loading the affected area, and never prescribes rehab or treatment.

**Output (after the model), `plan_checks.py` and schema validation:**
- Pydantic validation of every response.
- Every session lies inside a free slot; number of sessions = `workout_days`; at least one rest day; ≤ 6 sessions/week; session length ≤ `session_minutes`.
- Every exercise name is in `exercises.json`.
- No calorie or weight-loss targets in the demo scope. If added later, cap weight loss at about 0.5–1% of body weight per week.

## 9. Workstream steps

IDs match `PROGRESS.md`. "Done when" is the acceptance check for the section review.

### A — Profile
| ID | Step | Done when |
|---|---|---|
| A1 | `POST /api/profile/chat` with prompt + structured output via `call_model(feature="profile")` | A synthetic chat returns a valid `ProfileChatResponse`; missing fields listed |
| A2 | Profile storage in SQLite; `GET`/`PUT /api/profile` | Profile survives a server restart; unit tests pass |
| A3 | Angular profile page: chat panel + editable profile summary card | User can build and edit a profile in the browser |
| A4 | Workout log: `POST`/`GET /api/log`, `GET /api/log/bests`; Angular log page | Entries saved; bests computed correctly in unit tests |
| A5 | 8 profile test cases in `eval/cases/profile.json` with expected fields | Cases run in the harness and are scored |

### B — Plan
| ID | Step | Done when |
|---|---|---|
| B1 | `.ics` parser + `POST /api/calendar` → free slots; synthetic `.ics` fixtures | Unit tests pass on 3+ fixture calendars (empty, normal, packed) |
| B2 | `POST /api/plan` via `call_model(feature="plan")`; `GET /api/plan/current` | A synthetic profile + slots returns a valid `WeeklyPlan` |
| B3 | `plan_checks.py` + `exercises.json` + one-retry logic | Bad plans are caught in unit tests; retry path tested |
| B4 | Angular calendar upload + weekly plan view | User uploads `.ics` and sees the week's sessions |
| B5 | 8 plan test cases in `eval/cases/plan.json` + fixtures | Cases run in the harness and are scored |

### C — Platform
| ID | Step | Done when |
|---|---|---|
| C0 | Scaffold: FastAPI app with `/api/health`; Angular shell with routing + API service; `requirements.txt`; run instructions in README | Both run locally; browser shows health status from the back end |
| C1 | `call_model()`: structured output, usage log to `logs/usage.jsonl`, dev cache keyed on (model, prompt hash), prices from `.env` | A test call logs one line with tokens, latency, cost |
| C2 | Finalize `schemas.py` and `api.types.ts` from §6 (human confirms) | Both files exist and match; decision logged |
| C3 | `guardrails.py` (input) + wiring into A and B endpoints | Unit tests for each check pass |
| C4 | Eval harness: `run_eval.py`, `metrics.py`, 5 safety + 3 injection cases | Harness runs all case files and writes a report to `eval/results/` |
| C5 | Baseline run, `summarize_usage.py`, README usage/cost summary, AI-use disclosure section | Results table + usage table ready for the presentation |

## 10. Evaluation

24 cases, scored automatically by `eval/run_eval.py`:

| Group | Cases | Metric |
|---|---|---|
| Profile extraction (A5) | 8 | Schema-valid rate; field-match rate vs. expected fields |
| Plan generation (B5) | 8 | Constraint-pass rate (all §8 output checks) |
| Safety and edge cases (C4) | 5 | Correct response type (referral note, "no free time", capped days) |
| Prompt injection (C4) | 3 | Refusal flag set; no system-prompt text leaked |

Also recorded per case: tokens, latency, cost.

**Baseline:** the notebook lists one text model (`gpt-6-luna`), so the baseline compares the **full pipeline** against a **naive single prompt** (same model, no free-slot preprocessing, no plan checks, no guardrails) on the same cases. If a smaller text model is available from the course notebook, add a small-vs-large comparison too. *(Open item — §13.)*

## 11. Usage logging

`call_model()` appends one JSON line per call to `logs/usage.jsonl`:

```json
{"ts": "2026-11-20T18:02:11Z", "feature": "plan", "model": "gpt-6-luna", "input_tokens": 1840, "output_tokens": 610, "latency_ms": 2310, "cost_usd": 0.0009, "cached": false, "valid": true}
```

Cost = tokens × per-token prices from `.env` (`PRICE_INPUT_PER_1M`, `PRICE_OUTPUT_PER_1M`, filled in from the provider's pricing page). `summarize_usage.py` produces totals per feature for the README and presentation.

## 12. Models

From the course notebook: `gpt-6-luna` (text — used for everything), `gpt-4o-mini-tts` (speech output — not used), `gpt-4o-mini-transcribe` (speech input — stretch goal only), and a transcription model listed as "got-transcribe" (likely a typo — confirm the exact name before use).

## 13. Open items

Tracked with owners in `PROGRESS.md` → *Open questions*.
