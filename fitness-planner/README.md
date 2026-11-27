# Fitness Planner

An LLM-powered web app that builds a profile through chat and plans a week of workouts into your real free time. Built for the LLM Project Benchmark course, Colorado School of Mines, fall 2026.

**Team:** Jadon Minnick, Ethan Leuthauser, Ben Thiessen

> **Working on this project?** Start with [`docs/HOW_TO_START.md`](docs/HOW_TO_START.md).

## Status

See [`PROGRESS.md`](PROGRESS.md). Design: [`docs/DESIGN.md`](docs/DESIGN.md).

## Setup

You need Python 3.11 or newer and Node.js 22.22.3+ or 24.15+ (even-numbered LTS versions). Run everything from this folder (`fitness-planner/`).

> **First time, or setting up the front end?** Follow the step-by-step guide [`docs/FRONTEND_SETUP.md`](docs/FRONTEND_SETUP.md). It covers every page, the tests and troubleshooting.

**1. Settings.** Copy `.env.example` to `.env` and fill it in yourself. Never commit or share `.env`. Create it even without a key: the back-end command below will not start if `.env` is missing. Until the key arrives, leave `OPENAI_API_KEY=` and `OPENAI_MODEL=` empty, so no model call is attempted.

**2. Back end.**

Windows (PowerShell; if `python` opens the Microsoft Store, use `py` instead):

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Mac/Linux:

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

**3. Front end.** In a new terminal:

```bash
cd frontend
npm ci
```

## How to run the app

Use two terminals, both starting in `fitness-planner/`.

**Terminal 1: back end** (Windows, then Mac/Linux). `--env-file` loads your `.env`.

```powershell
cd backend
.venv\Scripts\python -m uvicorn app.main:app --port 8000 --env-file ../.env
```

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --port 8000 --env-file ../.env
```

**Terminal 2: front end.**

```bash
cd frontend
npm start
```

Open <http://localhost:4200>. The home page should say "Back end status: ok". Press Ctrl+C in each terminal to stop.

## How to run the tests

None of these call the OpenAI API.

Back end, from `backend/` (on Mac/Linux use `.venv/bin/python`):

```powershell
.venv\Scripts\python -m pytest
```

Front end, from `frontend/`:

```bash
npm test -- --watch=false
```

## Sections to complete (course requirements)

- [x] Setup instructions (step C0)
- [x] How to run the app (step C0)
- [ ] How to reproduce the evaluation (step C4)
- [ ] Models and providers used (step C5)
- [ ] Usage and cost summary (step C5)
- [ ] AI-use disclosure — summarized from [`docs/AI_USE.md`](docs/AI_USE.md) (step C5)
