# Front-end setup for teammates (Jadon, Ethan)

Step by step: get the web app (Angular front end + FastAPI back end) running on your machine, see every page in the browser, and know where to make front-end changes. About 15 minutes the first time. You do **not** need the API key for any of this.

If you use an AI agent, you can also just say: "Follow `docs/FRONTEND_SETUP.md` with me." It will still ask before each step.

---

## 1. Install the tools (once)

| Tool | Version | Check with |
|---|---|---|
| Git | any recent | `git --version` |
| Python | 3.11 or newer | `python --version` (Windows: `py --version`) |
| Node.js | **22.22.3+ or 24.15+** (Angular 22 needs one of these; Ben uses 24.22) | `node --version` |

- Get Node from nodejs.org (the "LTS" download). If `node --version` shows something older, install the new one and **open a new terminal**.
- You do **not** need to install Angular globally. `npm ci` installs the right version inside the project.

## 2. Get the latest code

In the repo folder (`AIFitnessProgram`):

```bash
git pull
```

Everything below runs from the `fitness-planner/` folder inside it.

## 3. Create `.env` (even without a key)

The back-end start command loads `.env`, and **it will not start if the file is missing**. Without a key, make the file anyway:

Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

Mac/Linux:

```bash
cp .env.example .env
```

Then open `.env` in a text editor and **make these two lines empty** until the key arrives:

```
OPENAI_API_KEY=
OPENAI_MODEL=
```

Leave the rest. With `OPENAI_MODEL` empty, `call_model()` stops before contacting OpenAI, so anything that needs the model shows a clear error and nothing is sent or charged. When the key arrives, paste it after `OPENAI_API_KEY=` yourself and set `OPENAI_MODEL=gpt-6-luna`. Never paste the key into an AI chat, a commit or the team chat. `.env` is gitignored.

## 4. Install the back end (once, and again when `requirements.txt` changes)

Windows (PowerShell; if `python` opens the Microsoft Store, use `py` instead):

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
cd ..
```

Mac/Linux:

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd ..
```

If you already had `.venv` from an older session, run just the `pip install` line again. Step B2 added a new package (`python-multipart`).

## 5. Install the front end (once, and again when `package-lock.json` changes)

```bash
cd frontend
npm ci
cd ..
```

`npm ci` installs exactly the versions in `package-lock.json` into `frontend/node_modules/` (gitignored). It takes a minute or two.

## 6. Run the app: two terminals

**Terminal 1, back end** (from `fitness-planner/`):

```powershell
cd backend
.venv\Scripts\python -m uvicorn app.main:app --port 8000 --env-file ../.env
```

On Mac/Linux, use `.venv/bin/python` instead. Leave it running. You should see `Uvicorn running on http://127.0.0.1:8000`.

**Terminal 2, front end** (from `fitness-planner/`):

```bash
cd frontend
npm start
```

Wait for `Local: http://localhost:4200/`, then open <http://localhost:4200>.

**Using the Claude Code desktop app instead?** The repo has `.claude/launch.json` with ready-made servers: `backend` (Windows) or `backend-mac-linux`, plus `frontend`. Ask the agent to start them in the browser pane. That back end does **not** load `.env`, which is fine without a key.

Stop the servers with **Ctrl+C** in each terminal.

## 7. Check every page (what works without a key)

Use made-up data only (course rule), for example "Sam Sample, 180 cm, 80 kg".

| Page | Try this | Without a key you should see |
|---|---|---|
| **Home** `/` | Open it | "Back end status: ok" |
| **Profile** `/profile` | Type in the chat; edit the card and press Save | Chat: "The assistant is unavailable right now…" (expected). Card: saves, and is still there after reloading the page |
| **Plan** `/plan` | Upload `fitness-planner/eval/fixtures/normal.ics`, then press "Make my plan" | The free times listed by day. "Make my plan" says "Finish your profile first…" until the core fields are filled in the profile card (height, weight, experience level, goals, workout days per week, session length). After that: "The model call failed: OPENAI_MODEL is not set" (expected without a key) |
| **Log** `/log` | Log an exercise with a weight | It appears in History and in Personal bests |

Your local data lives in `backend/data/app.db` (gitignored). Delete that file to start fresh. Stop the back end first.

## 8. Run the front-end tests

From `fitness-planner/frontend/`:

```bash
npm test -- --watch=false
```

Expect `80 passed` (as of 2026-11-26). Then check the production build:

```bash
npm run build
```

Neither command calls the API.

## 9. Where things are (for front-end work)

| Path | What it is |
|---|---|
| `frontend/src/app/app.routes.ts` | Pages and their URLs |
| `frontend/src/app/app.html` | The menu (Home · Profile · Plan · Log) |
| `frontend/src/app/core/api.types.ts` | **Shared contract**: TypeScript mirror of `backend/app/schemas.py`. Change it only with the team's OK (AGENTS.md §7) |
| `frontend/src/app/core/error-text.ts` | Turns a failed request into a readable message |
| `frontend/src/app/profile/` | Profile page (A3): chat + editable card, `profile.service.ts` |
| `frontend/src/app/plan/` | Plan page (B4): calendar upload + weekly plan, `plan.service.ts` |
| `frontend/src/app/log/` | Workout log page (A4), `log.service.ts` |
| `frontend/proxy.conf.json` | Sends `/api/...` from port 4200 to the back end on port 8000 |

Conventions (AGENTS.md §9): standalone components, one service per back-end area, types only from `api.types.ts`, a `.spec.ts` test next to each file. Styling is plain CSS per page, deliberately simple. Polishing the look for the demo video is Phase 4 work.

## 10. Troubleshooting

| Problem | Fix |
|---|---|
| `Error: Invalid value for '--env-file': Path '../.env' does not exist` | Do step 3, or run the back-end command from inside `backend/` |
| Home page says "Can't connect to the back end" (or another page says "Can't reach the back end") | Terminal 1 is not running, or not on port 8000 |
| `npm ci` complains about the Node version or fails | Check `node --version` against step 1, install a newer Node, open a new terminal, run `npm ci` again |
| `npm ci` says `package-lock.json` is out of sync | `git pull` again; don't run `npm install`, which changes the lock file. Ask the team if it persists |
| Port 4200 or 8000 already in use | Another copy is running. Close it (Ctrl+C in its terminal), or restart your computer |
| `python` opens the Microsoft Store (Windows) | Use `py -m venv .venv` in step 4 |
| `No module named 'multipart'` or another missing module | Rerun the `pip install -r requirements.txt` line from step 4 |
| Tests fail right after `git pull` | Rerun steps 4 and 5 (new packages), then the tests again. If they still fail, note it in `PROGRESS.md` → Open questions |

Still stuck? Tell your agent "explain this error" and paste the error text (never the key), or post it in the team chat.
