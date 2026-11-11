# Working with Gemini (or another AI) in a web browser

Use this only if you can't run Gemini CLI or Claude Code. A browser chat can't see the project or run anything, so **you** copy files in, apply its changes, and run git yourself. Everything else follows the same rules as `AGENTS.md`.

---

## Start of session

1. In a terminal in the project folder, run:
   - `git status` — shows whether you have unsaved changes. If it lists files, ask the team before going on.
   - `git pull` — downloads your teammates' latest work.
2. Open a new chat and paste this message, then paste the contents of `AGENTS.md`, `PROGRESS.md`, and `docs/DESIGN.md` under it:

```text
You are helping me work on a team project. The project rules are in AGENTS.md below — follow them exactly. You cannot run commands or edit files yourself: I will paste files you need and apply the changes you write. Whenever you change a file, give me the complete new file content with its path, never a partial snippet. Ask me rather than guessing. Start by asking me the questions in AGENTS.md section 5.1 step 4, then tell me the next step and which files you need to see. Wait for me to say "go" before writing any code.
```

3. Paste any other files the AI asks for. **Never paste `.env` or the API key.**

## While working

- For each change, the AI gives you the full file. Replace the file's contents in your editor and save.
- Run the tests or the app yourself when it asks, and paste the output back.
- Reviews: when a step is done, open a **second, fresh chat**, paste the changed files and the step's "Done when" line from `DESIGN.md` §9, and ask: "Review these files for bugs, typos, and mismatches with the design. Do not rewrite them; list problems only." Bring the findings back to your main chat.

## End of session

1. In your main chat, paste this:

```text
Wrap up. Write the updated PROGRESS.md sections following AGENTS.md section 5.3: Status board rows I touched, Next up, Open questions, Decisions log, and a new Session log entry using the template in PROGRESS.md (tool: Gemini web). Also write one row for docs/AI_USE.md. Give me complete text I can paste.
```

2. Paste the results into `PROGRESS.md` and `docs/AI_USE.md` and save.
3. In the terminal, run:
   - `git status` — check `.env` is **not** listed.
   - `git add -A` — stages all your changes.
   - `git commit -m "wrapup: <your name> <date> - <one-line summary>"` — saves a snapshot.
   - `git push` — uploads it for the next person.
4. If any git command shows an error or "conflict", stop and message the team before trying anything else.
