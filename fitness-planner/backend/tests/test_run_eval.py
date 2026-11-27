"""Offline tests for the eval harness eval/run_eval.py (Step C4).

A fake stands in for call_model() and writes usage lines like the real one,
so nothing here calls the API. Reports go to a temporary folder.
"""

from datetime import date
import json
from pathlib import Path
import sys
from typing import Any

import pytest

# Ensure fitness-planner root is on sys.path regardless of execution directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import db, llm, plan, profile
from backend.app.llm import LLMError
from backend.app.schemas import ProfileChatResponse, UserProfile, WeeklyPlan
from eval import run_eval

PROFILE_ID = "profile-01-all-in-one-metric"
PLAN_ID = "plan-01-beginner-3-days"
REFUSAL_ID = "plan-08-too-few-free-days"

# A perfect answer for profile-01 (see eval/cases/profile.json).
PROFILE_ANSWER = ProfileChatResponse(
    reply="Thanks! Does this look right?",
    profile=UserProfile(
        name="Alex Example",
        height_cm=172,
        weight_kg=68,
        experience="beginner",
        goals=["build strength"],
        workout_days=3,
        session_minutes=45,
    ),
    missing_fields=[],
)


def plan_answer(days: tuple[int, ...] = (0, 2, 4)) -> WeeklyPlan:
    """Sessions at 06:00 on the given days of the week of 2026-11-23."""
    sessions = [
        {
            "start": f"2026-11-{23 + d}T06:00:00",
            "end": f"2026-11-{23 + d}T06:45:00",
            "focus": "Full body",
            "exercises": [
                {"name": "Goblet squat", "activity_type": "strength", "sets": 3, "reps": 10}
            ],
        }
        for d in days
    ]
    return WeeklyPlan.model_validate(
        {"week_of": "2026-11-23", "sessions": sessions, "notes": []}
    )


class FakeModel:
    """Stands in for call_model(); logs usage like the real one."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.plan_answers: list[WeeklyPlan] = []
        self.fail_profile = False

    def __call__(self, feature, messages, response_model):
        self.calls.append(feature)
        llm._log_usage(feature, "fake-model", 100, 20, 7, 0.001, cached=False, valid=True)
        if feature == "profile":
            if self.fail_profile:
                raise LLMError("OpenAI call failed: APITimeoutError")
            return PROFILE_ANSWER
        if self.plan_answers:
            return self.plan_answers.pop(0)
        return plan_answer()


@pytest.fixture
def model(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeModel:
    fake = FakeModel()
    monkeypatch.setattr(profile, "call_model", fake)
    monkeypatch.setattr(plan, "call_model", fake)
    monkeypatch.setattr(llm, "USAGE_LOG", tmp_path / "usage.jsonl")
    monkeypatch.setenv("OPENAI_MODEL", "fake-model")
    monkeypatch.delenv("LLM_CACHE", raising=False)
    return fake


@pytest.fixture
def results(tmp_path: Path) -> Path:
    return tmp_path / "results"


def live(args: list[str], results: Path, tmp_path: Path) -> int:
    return run_eval.main(
        [*args, "--live"], env_file=tmp_path / "no.env", results_dir=results
    )


def report(results: Path) -> dict[str, Any]:
    [path] = results.glob("*-pipeline.json")
    return json.loads(path.read_text(encoding="utf-8"))


# --- without --live nothing runs ---


def test_listing_makes_no_calls_and_writes_nothing(
    model: FakeModel, results: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run_eval.main([], results_dir=results) == 0
    out = capsys.readouterr().out
    assert model.calls == []
    assert not results.exists()
    assert PROFILE_ID in out and REFUSAL_ID in out
    assert "17 cases, up to 23 model calls. Nothing was run." in out


def test_listing_one_group(model: FakeModel, capsys: pytest.CaptureFixture[str]) -> None:
    run_eval.main(["--group", "plan"])
    assert "8 cases, up to 14 model calls." in capsys.readouterr().out


def test_live_without_a_model_setting_runs_nothing(
    model: FakeModel,
    results: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("OPENAI_MODEL")
    assert live([], results, tmp_path) == 1
    assert model.calls == []
    assert not results.exists()
    assert "OPENAI_MODEL is not set" in capsys.readouterr().out


def test_unknown_case_id_stops_before_anything_runs(model: FakeModel) -> None:
    with pytest.raises(SystemExit, match="Unknown case id"):
        run_eval.main(["--only", "profile-99-nope", "--live"])
    assert model.calls == []


# --- live runs with the fake model ---


def test_live_run_scores_and_reports(
    model: FakeModel, results: Path, tmp_path: Path
) -> None:
    assert live(["--only", PROFILE_ID, PLAN_ID, REFUSAL_ID], results, tmp_path) == 0
    assert model.calls == ["profile", "plan"]  # the refusal makes no call
    data = report(results)
    assert data["run"]["mode"] == "pipeline"
    assert data["run"]["model"] == "fake-model"
    assert data["run"]["cache"] is True
    by_id = {case["id"]: case for case in data["cases"]}
    assert by_id[PROFILE_ID]["checks_passed"] == by_id[PROFILE_ID]["checks_total"]
    assert by_id[PLAN_ID]["constraint_pass"] is True
    assert by_id[REFUSAL_ID]["status"] == 400
    assert by_id[REFUSAL_ID]["checks_passed"] == 3
    assert data["summary"]["profile"]["schema_valid_rate"] == 1.0
    assert data["summary"]["plan"]["constraint_pass_rate"] == 1.0
    assert by_id[PLAN_ID]["usage"] == {
        "calls": 1,
        "unreadable_lines": 0,
        "cached_calls": 0,
        "input_tokens": 100,
        "output_tokens": 20,
        "latency_ms": 7,
        "cost_usd": 0.001,
    }
    assert by_id[REFUSAL_ID]["usage"]["calls"] == 0
    [md] = results.glob("*-pipeline.md")
    assert PLAN_ID in md.read_text(encoding="utf-8")


def test_report_holds_no_chat_or_profile_text(
    model: FakeModel, results: Path, tmp_path: Path
) -> None:
    live(["--only", PROFILE_ID, PLAN_ID], results, tmp_path)
    text = "".join(p.read_text(encoding="utf-8") for p in results.iterdir())
    assert "Alex Example" not in text
    assert "172 cm and 68 kg" not in text
    assert "build strength" not in text


def test_a_retried_plan_counts_two_calls(
    model: FakeModel, results: Path, tmp_path: Path
) -> None:
    model.plan_answers = [plan_answer((0, 2)), plan_answer()]  # 2 sessions, then 3
    live(["--only", PLAN_ID], results, tmp_path)
    [case] = report(results)["cases"]
    assert case["usage"]["calls"] == 2
    assert case["constraint_pass"] is True


def test_a_plan_failing_twice_is_scored_as_a_fail(
    model: FakeModel, results: Path, tmp_path: Path
) -> None:
    model.plan_answers = [plan_answer((0, 2)), plan_answer((0, 2))]
    live(["--only", PLAN_ID], results, tmp_path)
    [case] = report(results)["cases"]
    assert case["status"] == 502
    assert case["constraint_pass"] is False
    assert case["checks_passed"] == 0


def test_a_model_failure_does_not_stop_the_run(
    model: FakeModel, results: Path, tmp_path: Path
) -> None:
    model.fail_profile = True
    assert live(["--only", PROFILE_ID, PLAN_ID], results, tmp_path) == 0
    by_id = {case["id"]: case for case in report(results)["cases"]}
    assert by_id[PROFILE_ID]["status"] == 502
    assert by_id[PROFILE_ID]["checks_passed"] == 0
    assert by_id[PLAN_ID]["constraint_pass"] is True


def test_a_harness_error_fails_only_that_case(
    model: FakeModel,
    results: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = run_eval.run_profile_case

    def broken(client, case):
        raise RuntimeError("boom")

    monkeypatch.setattr(run_eval, "run_profile_case", broken)
    live(["--only", PROFILE_ID, PLAN_ID], results, tmp_path)
    by_id = {case["id"]: case for case in report(results)["cases"]}
    assert by_id[PROFILE_ID]["error"] == "RuntimeError"
    assert by_id[PROFILE_ID]["checks_passed"] == 0
    assert by_id[PLAN_ID]["error"] is None
    monkeypatch.setattr(run_eval, "run_profile_case", real)


def test_cache_flag_sets_llm_cache_during_the_run_only(
    model: FakeModel,
    results: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import os

    seen: list[str | None] = []

    def spy(feature, messages, response_model):
        seen.append(os.environ.get("LLM_CACHE"))
        return PROFILE_ANSWER

    monkeypatch.setattr(profile, "call_model", spy)
    live(["--only", PROFILE_ID], results, tmp_path)
    live(["--only", PROFILE_ID, "--no-cache"], results, tmp_path)
    assert seen == ["1", "0"]
    assert "LLM_CACHE" not in os.environ  # restored afterwards

    monkeypatch.setenv("LLM_CACHE", "keep-me")
    live(["--only", PROFILE_ID], results, tmp_path)
    assert os.environ["LLM_CACHE"] == "keep-me"


def test_broken_usage_log_lines_do_not_lose_the_run(
    model: FakeModel, results: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def half_written(feature, messages, response_model):
        with open(llm.USAGE_LOG, "a", encoding="utf-8") as log:
            log.write('{"feature": "profile", "input_tok\n[1, 2]\n')
        llm._log_usage(feature, "fake-model", 100, 20, 7, 0.001, cached=False, valid=True)
        return PROFILE_ANSWER

    monkeypatch.setattr(profile, "call_model", half_written)
    assert live(["--only", PROFILE_ID], results, tmp_path) == 0
    [case] = report(results)["cases"]
    assert case["usage"]["calls"] == 1
    assert case["usage"]["unreadable_lines"] == 2
    assert case["checks_passed"] == case["checks_total"]


def test_missing_fixture_fails_only_that_case(
    model: FakeModel, results: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run_eval, "FIXTURES_DIR", tmp_path / "no-fixtures")
    live(["--only", PROFILE_ID, PLAN_ID], results, tmp_path)
    by_id = {case["id"]: case for case in report(results)["cases"]}
    assert by_id[PLAN_ID]["error"] == "FileNotFoundError"
    assert by_id[PLAN_ID]["constraint_pass"] is False
    assert by_id[PROFILE_ID]["error"] is None


def test_profile_only_run_has_no_plan_summary(
    model: FakeModel, results: Path, tmp_path: Path
) -> None:
    live(["--group", "profile", "--only", PROFILE_ID], results, tmp_path)
    data = report(results)
    assert set(data["summary"]) == {"profile"}
    [md] = results.glob("*-pipeline.md")
    assert "a missed core field costs two checks" in md.read_text(encoding="utf-8")


def test_runs_in_the_same_second_do_not_overwrite(
    model: FakeModel, results: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FixedClock:
        @staticmethod
        def now(tz=None):
            from datetime import datetime

            return datetime(2026, 11, 26, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr(run_eval, "datetime", FixedClock)
    live(["--only", PROFILE_ID], results, tmp_path)
    live(["--only", PROFILE_ID], results, tmp_path)
    names = sorted(p.name for p in results.iterdir())
    assert names == [
        "20261126T120000Z-pipeline-2.json",
        "20261126T120000Z-pipeline-2.md",
        "20261126T120000Z-pipeline.json",
        "20261126T120000Z-pipeline.md",
    ]


def test_report_counts_plan_problems_without_their_text(
    model: FakeModel, results: Path, tmp_path: Path
) -> None:
    # In the pipeline a plan with problems ends as a 502 (nothing to check), so
    # make the harness score a 200 plan that breaks a rule.
    monkeypatch_target = run_eval.metrics

    def score_with_problem(case, status, body, slots):
        score = original(case, status, body, slots)
        score.problems = ['Session 1: "Secret Persona Move" is not on the exercise list.']
        return score

    original = monkeypatch_target.score_plan
    monkeypatch_target.score_plan = score_with_problem
    try:
        live(["--only", PLAN_ID], results, tmp_path)
    finally:
        monkeypatch_target.score_plan = original
    [reported] = report(results)["cases"]
    assert "problems" not in reported
    assert reported["plan_problems"] == 1
    text = "".join(p.read_text(encoding="utf-8") for p in results.iterdir())
    assert "Secret Persona Move" not in text


def test_cases_do_not_touch_the_real_database_or_week(
    model: FakeModel, results: Path, tmp_path: Path
) -> None:
    real_db, real_today = db.DB_PATH, plan.today
    live(["--only", PROFILE_ID, PLAN_ID], results, tmp_path)
    assert db.DB_PATH == real_db
    assert plan.today is real_today
    assert plan.today() == date.today()


def test_each_case_starts_with_an_empty_database(
    model: FakeModel, results: Path, tmp_path: Path
) -> None:
    seen: list[UserProfile] = []
    real = profile.call_model

    def spy(feature, messages, response_model):
        seen.append(db.load_profile())
        return real(feature, messages, response_model)

    profile.call_model = spy
    try:
        live(["--only", PROFILE_ID, "profile-02-imperial-units"], results, tmp_path)
    finally:
        profile.call_model = real
    assert seen == [UserProfile(), UserProfile()]


def test_cached_calls_count_no_tokens_or_cost(
    model: FakeModel, results: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def cached(feature, messages, response_model):
        llm._log_usage(feature, "fake-model", 0, 0, 0, 0.0, cached=True, valid=True)
        return PROFILE_ANSWER

    monkeypatch.setattr(profile, "call_model", cached)
    live(["--only", PROFILE_ID], results, tmp_path)
    [case] = report(results)["cases"]
    assert case["usage"]["calls"] == 1
    assert case["usage"]["cached_calls"] == 1
    assert case["usage"]["input_tokens"] == 0
    assert case["usage"]["cost_usd"] == 0


def test_unknown_cost_stays_unknown(
    model: FakeModel, results: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_price(feature, messages, response_model):
        llm._log_usage(feature, "fake-model", 100, 20, 7, None, cached=False, valid=True)
        return PROFILE_ANSWER

    monkeypatch.setattr(profile, "call_model", no_price)
    live(["--only", PROFILE_ID], results, tmp_path)
    [case] = report(results)["cases"]
    assert case["usage"]["cost_usd"] is None
    assert case["usage"]["input_tokens"] == 100
