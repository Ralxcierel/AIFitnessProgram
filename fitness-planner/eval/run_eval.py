"""Run the eval cases through the real pipeline and score them (Step C4).

Usage, from the fitness-planner folder:

    backend/.venv/Scripts/python eval/run_eval.py                 # list only, no API calls
    backend/.venv/Scripts/python eval/run_eval.py --only profile-01-all-in-one-metric --live
    backend/.venv/Scripts/python eval/run_eval.py --group plan --live --no-cache

Without --live nothing calls the model: the cases and the most model calls they
could make are listed. With --live, settings come from fitness-planner/.env
(never printed). Every case runs in-process through the FastAPI app with its
own throwaway database. Results go to eval/results/<timestamp>-pipeline.json
and .md: scores and usage only, never chat or profile text.
"""

import argparse
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from fastapi.testclient import TestClient

from backend.app import db, llm, plan
from backend.app.main import app as api_app
from backend.app.calendar_ics import find_free_slots
from backend.app.schemas import FreeSlot, UserProfile
from eval import metrics

CASES_DIR = PROJECT_ROOT / "eval" / "cases"
FIXTURES_DIR = PROJECT_ROOT / "eval" / "fixtures"
RESULTS_DIR = PROJECT_ROOT / "eval" / "results"
ENV_FILE = PROJECT_ROOT / ".env"
GROUPS = ("profile", "plan")


# --- loading cases ---


def load_group(group: str) -> dict[str, Any]:
    """One case file, e.g. eval/cases/plan.json."""
    return json.loads((CASES_DIR / f"{group}.json").read_text(encoding="utf-8"))


def select_cases(
    groups: Sequence[str], only: Sequence[str] | None
) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    """(group, case, file data) for every chosen case, in file order."""
    chosen = []
    for group in groups:
        data = load_group(group)
        for case in data["cases"]:
            if not only or case["id"] in only:
                chosen.append((group, case, data))
    if only:
        unknown = set(only) - {case["id"] for _, case, _ in chosen}
        if unknown:
            raise SystemExit(f"Unknown case id(s): {', '.join(sorted(unknown))}")
    return chosen


def max_calls(group: str, case: dict[str, Any]) -> int:
    """The most model calls a case can make in the pipeline."""
    if group == "plan":
        return 2 if case["expect"]["status"] == 200 else 0  # one retry; refusals: none
    return 1


# --- running one case ---


@contextmanager
def isolated(week_of: date | None) -> Iterator[None]:
    """A throwaway database, and (for plan cases) a fixed calendar week."""
    old_db, old_today = db.DB_PATH, plan.today
    with tempfile.TemporaryDirectory() as tmp:
        db.DB_PATH = Path(tmp) / "app.db"
        if week_of is not None:
            plan.today = lambda: week_of
        try:
            yield
        finally:
            db.DB_PATH, plan.today = old_db, old_today


def response_parts(result: Any) -> tuple[int, Any]:
    """Status code and JSON body (None if the body is not JSON)."""
    try:
        return result.status_code, result.json()
    except ValueError:
        return result.status_code, None


def run_profile_case(client: TestClient, case: dict[str, Any]) -> metrics.CaseScore:
    with isolated(None):
        if case["saved_profile"] is not None:
            db.save_profile(UserProfile.model_validate(case["saved_profile"]))
        status, body = response_parts(
            client.post("/api/profile/chat", json={"messages": case["messages"]})
        )
    return metrics.score_profile(case, status, body)


def run_plan_case(
    client: TestClient, case: dict[str, Any], week_of: date
) -> metrics.CaseScore:
    fixture = (FIXTURES_DIR / case["calendar"]).read_bytes()
    slots: list[FreeSlot] = find_free_slots(fixture, start_date=week_of)
    with isolated(week_of):
        db.save_profile(UserProfile.model_validate(case["saved_profile"]))
        files = {"file": (case["calendar"], fixture, "text/calendar")}
        upload = client.post("/api/calendar", files=files)
        if upload.status_code != 200:
            raise RuntimeError(f"calendar upload failed with {upload.status_code}")
        status, body = response_parts(client.post("/api/plan"))
    return metrics.score_plan(case, status, body, slots)


def run_case(
    client: TestClient, group: str, case: dict[str, Any], data: dict[str, Any]
) -> dict[str, Any]:
    """Run and score one case; an error fails the case but not the run."""
    lines_before = _usage_line_count()
    error = None
    try:
        if group == "profile":
            score = run_profile_case(client, case)
        else:
            score = run_plan_case(client, case, date.fromisoformat(data["week_of"]))
    except Exception as err:  # noqa: BLE001 - one broken case must not stop the run
        error = type(err).__name__
        score = _failed_score(group, case)
    return {
        "id": case["id"],
        "group": group,
        "status": score.status,
        "schema_valid": score.schema_valid,
        "constraint_pass": score.constraint_pass,
        "checks_passed": score.passed,
        "checks_total": score.total,
        "checks": [{"name": name, "passed": ok} for name, ok in score.checks],
        # Only the count: problem texts can quote model-written exercise names.
        "plan_problems": len(score.problems),
        "error": error,
        "usage": usage_since(lines_before),
        "_score": score,
    }


def _failed_score(group: str, case: dict[str, Any]) -> metrics.CaseScore:
    """A case that could not run: every check fails."""
    names = (
        metrics.profile_check_names(case["expect"])
        if group == "profile"
        else metrics.plan_check_names(case["expect"])
    )
    score = metrics.CaseScore(id=case["id"], group=group, status=None, schema_valid=False)
    score.checks = [(name, False) for name in names]
    if group == "plan" and case["expect"]["status"] == 200:
        score.constraint_pass = False
    return score


# --- usage log ---


def _usage_line_count() -> int:
    try:
        with open(llm.USAGE_LOG, encoding="utf-8") as log:
            return sum(1 for _ in log)
    except FileNotFoundError:
        return 0


def usage_since(line_count: int) -> dict[str, Any]:
    """Totals of the usage-log lines written after `line_count` lines."""
    try:
        with open(llm.USAGE_LOG, encoding="utf-8") as log:
            lines = log.readlines()[line_count:]
    except FileNotFoundError:
        lines = []
    entries, unreadable = [], 0
    for line in lines:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            entry = None
        if isinstance(entry, dict):
            entries.append(entry)
        else:
            unreadable += 1  # a broken line must not lose a paid run
    live = [e for e in entries if not e.get("cached")]
    return {
        "calls": len(entries),
        "unreadable_lines": unreadable,
        "cached_calls": len(entries) - len(live),
        "input_tokens": _total(e.get("input_tokens") for e in live),
        "output_tokens": _total(e.get("output_tokens") for e in live),
        "latency_ms": sum(e.get("latency_ms") or 0 for e in entries),
        "cost_usd": _total(e.get("cost_usd") for e in live),
    }


def _total(values: Any) -> float | int | None:
    """Sum, or None if any value is unknown (null in the log)."""
    total = 0
    for value in values:
        if value is None:
            return None
        total += value
    return total


# --- reports ---


def write_report(
    results: list[dict[str, Any]], run_info: dict[str, Any], out_dir: Path
) -> tuple[Path, Path]:
    """Save <timestamp>-pipeline.json and .md; return both paths."""
    summary = metrics.summarize([r["_score"] for r in results])
    cases = [{k: v for k, v in r.items() if k != "_score"} for r in results]
    report = {"run": run_info, "summary": summary, "cases": cases}
    out_dir.mkdir(parents=True, exist_ok=True)
    base = f"{run_info['started'].replace(':', '').replace('-', '')}-{run_info['mode']}"
    stem, n = base, 1
    while (out_dir / f"{stem}.json").exists() or (out_dir / f"{stem}.md").exists():
        n += 1
        stem = f"{base}-{n}"  # two runs in the same second must not overwrite
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(markdown_report(report), encoding="utf-8")
    return json_path, md_path


def markdown_report(report: dict[str, Any]) -> str:
    run = report["run"]
    lines = [
        f"# Eval run {run['started']} ({run['mode']})",
        "",
        f"Model: `{run['model']}` · cache: {'on' if run['cache'] else 'off'} · "
        f"cases: {len(report['cases'])}",
        "",
        "| Group | Cases | Schema-valid | Constraint-pass | Check-pass |",
        "|---|---|---|---|---|",
    ]
    for group, row in report["summary"].items():
        lines.append(
            f"| {group} | {row['cases']} | {_pct(row.get('schema_valid_rate'))} | "
            f"{_pct(row.get('constraint_pass_rate'))} | {_pct(row['check_pass_rate'])} "
            f"({row['checks_passed']}/{row['checks_total']}) |"
        )
    lines += [
        "",
        "| Case | Status | Checks | Calls | Tokens in/out | Latency ms | Cost USD | Error |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for case in report["cases"]:
        u = case["usage"]
        lines.append(
            f"| {case['id']} | {case['status']} | {case['checks_passed']}/{case['checks_total']} | "
            f"{u['calls']} ({u['cached_calls']} cached) | {u['input_tokens']}/{u['output_tokens']} | "
            f"{u['latency_ms']} | {u['cost_usd']} | {case['error'] or ''} |"
        )
    lines += [
        "",
        "Profile cases: a missed core field costs two checks (its `empty` or value "
        "check and `missing_fields`). Plan constraint-pass counts only cases that "
        "expect a plan (HTTP 200).",
    ]
    return "\n".join(lines) + "\n"


def _pct(rate: float | None) -> str:
    return "—" if rate is None else f"{rate:.0%}"


# --- command line ---


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run and score the eval cases.")
    parser.add_argument("--group", choices=[*GROUPS, "all"], default="all")
    parser.add_argument("--only", nargs="+", metavar="CASE_ID", help="run just these cases")
    parser.add_argument("--live", action="store_true", help="really call the model")
    parser.add_argument("--no-cache", action="store_true", help="skip the dev response cache")
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    *,
    env_file: Path = ENV_FILE,
    results_dir: Path = RESULTS_DIR,
) -> int:
    args = parse_args(argv)
    groups = GROUPS if args.group == "all" else (args.group,)
    chosen = select_cases(groups, args.only)
    calls = sum(max_calls(group, case) for group, case, _ in chosen)

    if not args.live:
        for group, case, _ in chosen:
            print(f"{group:8} {case['id']}  (up to {max_calls(group, case)} model calls)")
        print(f"\n{len(chosen)} cases, up to {calls} model calls. Nothing was run.")
        print("Add --live to call the model (it costs money).")
        return 0

    load_dotenv(env_file, override=False)
    model = os.environ.get("OPENAI_MODEL", "").strip()
    if not model:
        print("OPENAI_MODEL is not set (see .env.example). Nothing was run.")
        return 1
    old_cache = os.environ.get("LLM_CACHE")
    os.environ["LLM_CACHE"] = "0" if args.no_cache else "1"
    try:
        return run_live(chosen, calls, model, args, results_dir)
    finally:
        # Leave the caller's environment as it was.
        if old_cache is None:
            os.environ.pop("LLM_CACHE", None)
        else:
            os.environ["LLM_CACHE"] = old_cache


def run_live(
    chosen: list[tuple[str, dict[str, Any], dict[str, Any]]],
    calls: int,
    model: str,
    args: argparse.Namespace,
    results_dir: Path,
) -> int:
    """Run the chosen cases against the model and write the report."""

    run_info = {
        "started": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "pipeline",
        "model": model,
        "cache": not args.no_cache,
        "case_ids": [case["id"] for _, case, _ in chosen],
    }
    print(f"Running {len(chosen)} cases (up to {calls} model calls)...")
    client = TestClient(api_app, raise_server_exceptions=False)
    results = []
    for group, case, data in chosen:
        result = run_case(client, group, case, data)
        mark = "error" if result["error"] else f"{result['checks_passed']}/{result['checks_total']}"
        print(f"  {case['id']}: {mark}")
        results.append(result)
    json_path, md_path = write_report(results, run_info, results_dir)
    print(f"Report: {json_path}")
    print(f"        {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
