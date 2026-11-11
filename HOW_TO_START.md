# How to start a work session

You don't need to know the AI rules to work on this project. The agent reads them itself. You type two commands, answer its questions, and approve what it wants to do.

---

## One-time setup (first session only)

1. **Install the basics** (skip any you already have):
   - Git
   - Python 3.11 or newer
   - Node.js (LTS version)
2. **Install one AI coding tool** and sign in:
   - **Claude Code** — follow the install steps at docs.claude.com (Claude Code section).
   - **Gemini CLI** — in a terminal, run `npm install -g @google/gemini-cli`, then run `gemini` once to sign in.
3. **Get the project:** in a terminal, go to where you keep projects and run
   `git clone <our repo link>`
   (the link is in the team chat or the README).
4. **Add the API key yourself — never through the AI:**
   - In the project folder, copy `.env.example` to a new file named `.env`.
   - Open `.env` in a text editor and paste the key the instructor sent, after `OPENAI_API_KEY=`.
   - Never paste the key into an AI chat, a commit, a screenshot, or the team chat.

## Every session

1. Open a terminal **in the project folder**.
2. Start your tool: type `claude` or `gemini` and press Enter.
3. Type **`/start`** and press Enter.
4. The agent will:
   - download your teammates' latest work (after you say yes);
   - ask your name, your workstream (A, B, or C), how much time you have, and whether anything changed;
   - tell you where things stand and what it plans to do next.
5. Say **"go"** when the plan looks right. Then approve or deny each action it asks about.
6. When you're done, type **`/wrapup`**. The agent records what happened in `PROGRESS.md`, saves and uploads the work (after you say yes), and tells you what the next person will see.

**Always `/wrapup` before you close the terminal.** Otherwise the next person can't pick up where you left off.

## What the agent will ask permission for

It asks before it creates, changes, or deletes any file; runs anything that changes something; uses git beyond looking; or calls the OpenAI API (that costs money). It may read files without asking.

You can answer:
- **"yes"** / **"go"** — do it.
- **"no"** — don't. It will suggest something else.
- **"explain"** — tell me what that does in plain words first.
- **"stop"** — stop what you're doing right now.
- **"undo that"** — revert the last change.
- **"pass on <something specific>"** — e.g. "pass on small edits inside `plan.py`". It stops asking about that kind of action for the rest of this session (but still tells you). A pass never covers deleting files, pushing, API runs, or moving to the next phase.

## Tips

- You're in charge. If something seems off, say so. The agent is told to ask rather than guess.
- If you don't understand something, ask: "explain that like I'm new to this."
- Don't turn on auto-accept modes (Claude Code's auto-accept edits, Gemini's YOLO mode). Every change should go past you.
- If git shows a scary message, don't try to fix it yourself. Ask the agent to explain, or message the team.
- Using Gemini in a web browser instead of the CLI? See `docs/WEB_CHAT_HANDOFF.md`.

## Where things are

| File | What it is |
|---|---|
| `PROGRESS.md` | Where we are, what's next, open questions, session history |
| `docs/DESIGN.md` | What we're building — features, API, schemas, tests |
| `AGENTS.md` | The rules the AI follows (you can read it, but you don't have to) |
| `docs/AI_USE.md` | Log of how we used AI (required by the course) |
