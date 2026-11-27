"""Offline checks that the eval case files are well-formed (Steps A5, B5).

These tests only read the case files and fixture calendars; nothing here calls
the API. The matching rules are described in eval/cases/README.md.
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

from backend.app import guardrails, plan, plan_checks
from backend.app.calendar_ics import find_free_slots
from backend.app.profile import CORE_FIELDS, ProfileChatRequest, missing_fields
from backend.app.schemas import UserProfile

CASE_FILE = PROJECT_ROOT / "eval" / "cases" / "profile.json"
RULES = {"refused", "exact", "approx", "contains", "empty", "missing_fields"}
LIST_FIELDS = {
    name
    for name, field in UserProfile.model_fields.items()
    if getattr(field.annotation, "__origin__", None) is list
}

DATA: dict[str, Any] = json.loads(CASE_FILE.read_text(encoding="utf-8"))
CASES: list[dict[str, Any]] = DATA["cases"]
IDS = [case["id"] for case in CASES]


def test_file_header() -> None:
    assert DATA["group"] == "profile"
    assert DATA["step"] == "A5"
    assert DATA["endpoint"] == "POST /api/profile/chat"


def test_there_are_nine_cases_with_unique_ids() -> None:
    # DESIGN.md §10 asks for 8; a 9th (vague answers) was added on 2026-11-26.
    assert len(CASES) == 9
    assert len(set(IDS)) == len(IDS)
    assert all(case_id.startswith("profile-") for case_id in IDS)


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_case_has_the_expected_keys(case: dict[str, Any]) -> None:
    assert set(case) == {"id", "description", "saved_profile", "messages", "expect"}
    assert case["description"].strip()
    assert set(case["expect"]) == RULES


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_messages_are_a_valid_chat_request(case: dict[str, Any]) -> None:
    ProfileChatRequest.model_validate({"messages": case["messages"]})


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_saved_profile_is_a_valid_profile(case: dict[str, Any]) -> None:
    saved = case["saved_profile"]
    if saved is None:
        return
    # UserProfile ignores unknown keys, so check the names ourselves.
    assert set(saved) <= set(UserProfile.model_fields), "misspelled field name"
    UserProfile.model_validate(saved, strict=True)


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_rules_name_real_fields_once(case: dict[str, Any]) -> None:
    expect = case["expect"]
    named = [
        *expect["exact"],
        *expect["approx"],
        *expect["contains"],
        *expect["empty"],
    ]
    assert set(named) <= set(UserProfile.model_fields)
    assert len(named) == len(set(named)), "a field is named by more than one rule"


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_exact_and_approx_values_are_allowed_values(case: dict[str, Any]) -> None:
    expect = case["expect"]
    # Strict: "3" (text) must not pass for 3, or the scorer would never match it.
    UserProfile.model_validate(expect["exact"], strict=True)
    for field, rule in expect["approx"].items():
        assert set(rule) == {"value", "tolerance"}
        assert rule["tolerance"] > 0
        UserProfile.model_validate({field: rule["value"]}, strict=True)


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_contains_rules_are_keyword_groups(case: dict[str, Any]) -> None:
    for field, groups in case["expect"]["contains"].items():
        assert field in LIST_FIELDS or field in {"name", "split_preference", "health_notes"}
        assert groups, f"{field}: no keyword groups"
        for group in groups:
            assert group and all(isinstance(word, str) and word.strip() for word in group)


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_missing_fields_match_the_empty_core_fields(case: dict[str, Any]) -> None:
    """Python computes missing_fields, so the expected list must agree with the rules."""
    expect = case["expect"]
    empty_core = [field for field in CORE_FIELDS if field in expect["empty"]]
    assert expect["missing_fields"] == empty_core
    filled = {*expect["exact"], *expect["approx"], *expect["contains"]}
    for field in CORE_FIELDS:
        assert field in filled or field in expect["empty"], f"{field} has no rule"


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_refused_is_false_for_every_profile_case(case: dict[str, Any]) -> None:
    # Refusal and injection cases belong to C4, not A5.
    assert case["expect"]["refused"] is False


# --- plan.json (Step B5) ---

PLAN_FILE = PROJECT_ROOT / "eval" / "cases" / "plan.json"
FIXTURES = PROJECT_ROOT / "eval" / "fixtures"
PLAN_RULES = {
    "status",
    "passes_checks",
    "session_count",
    "notes_contain",
    "detail_contains",
    "exercises_exclude",
}
OPTIONAL_PLAN_RULES = {"notes_exclude", "model_calls_max"}

PLAN_DATA: dict[str, Any] = json.loads(PLAN_FILE.read_text(encoding="utf-8"))
PLAN_CASES: list[dict[str, Any]] = PLAN_DATA["cases"]
PLAN_IDS = [case["id"] for case in PLAN_CASES]
WEEK_OF = date.fromisoformat(PLAN_DATA["week_of"])


def free_days_in(calendar: str) -> int:
    """Days with free time in a fixture calendar, for the case week."""
    data = (FIXTURES / calendar).read_bytes()
    return len(plan_checks.free_days(find_free_slots(data, start_date=WEEK_OF)))


def assert_keyword_groups(groups: Any) -> None:
    assert isinstance(groups, list)
    for group in groups:
        assert group and all(isinstance(word, str) and word.strip() for word in group)


def test_plan_file_header() -> None:
    assert PLAN_DATA["group"] == "plan"
    assert PLAN_DATA["step"] == "B5"
    assert PLAN_DATA["endpoint"] == "POST /api/plan"
    assert WEEK_OF.weekday() == 0, "week_of should be a Monday"


def test_there_are_eight_plan_cases_with_unique_ids() -> None:
    assert len(PLAN_CASES) == 8
    assert len(set(PLAN_IDS)) == len(PLAN_IDS)
    assert all(case_id.startswith("plan-") for case_id in PLAN_IDS)


@pytest.mark.parametrize("case", PLAN_CASES, ids=PLAN_IDS)
def test_plan_case_has_the_expected_keys(case: dict[str, Any]) -> None:
    assert set(case) == {"id", "description", "saved_profile", "calendar", "expect"}
    assert case["description"].strip()
    assert set(case["expect"]) - OPTIONAL_PLAN_RULES == PLAN_RULES


@pytest.mark.parametrize("case", PLAN_CASES, ids=PLAN_IDS)
def test_plan_saved_profile_is_complete_and_valid(case: dict[str, Any]) -> None:
    check_complete_profile(case)


def check_complete_profile(case: dict[str, Any]) -> None:
    """Shared with the plan-kind safety and injection cases."""
    saved = case["saved_profile"]
    assert set(saved) <= set(UserProfile.model_fields), "misspelled field name"
    profile = UserProfile.model_validate(saved, strict=True)
    # Otherwise the plan endpoint refuses with "Finish your profile first".
    assert missing_fields(profile) == []


@pytest.mark.parametrize("case", PLAN_CASES, ids=PLAN_IDS)
def test_plan_calendar_is_a_fixture(case: dict[str, Any]) -> None:
    assert (FIXTURES / case["calendar"]).is_file()


@pytest.mark.parametrize("case", PLAN_CASES, ids=PLAN_IDS)
def test_plan_expectations_fit_the_status(case: dict[str, Any]) -> None:
    check_status_rules(case)


def check_status_rules(case: dict[str, Any]) -> None:
    """Shared with the plan-kind safety and injection cases."""
    expect = case["expect"]
    workout_days = case["saved_profile"]["workout_days"]
    assert expect["status"] in {200, 400}
    for rule in ("notes_contain", "detail_contains"):
        assert_keyword_groups(expect[rule])
    words = expect.get("notes_exclude", [])
    assert all(isinstance(w, str) and w and w == w.strip().lower() for w in words)
    assert not (words and expect["status"] != 200), "notes_exclude needs a plan"
    # The fixed health note must never trip the calorie check.
    assert not any(w in plan.HEALTH_NOTE.lower() for w in words)
    if expect["status"] == 200:
        # eval/metrics.py always scores passes_checks as "must pass".
        assert expect["passes_checks"] is True
        assert expect["session_count"] == workout_days
        assert expect["detail_contains"] == []
    else:
        assert expect["passes_checks"] is None
        assert expect["session_count"] is None
        assert expect["notes_contain"] == []
        assert expect["exercises_exclude"] == []
        assert expect["detail_contains"], "a refusal case needs its message checked"


@pytest.mark.parametrize("case", PLAN_CASES, ids=PLAN_IDS)
def test_plan_case_is_possible_or_refused_on_its_calendar(case: dict[str, Any]) -> None:
    """A 200 case must have enough free days; a 400 case must really have too few."""
    days = free_days_in(case["calendar"])
    enough = days >= case["saved_profile"]["workout_days"]
    assert enough == (case["expect"]["status"] == 200)


@pytest.mark.parametrize("case", PLAN_CASES, ids=PLAN_IDS)
def test_excluded_words_leave_enough_exercises(case: dict[str, Any]) -> None:
    words = case["expect"]["exercises_exclude"]
    assert all(isinstance(w, str) and w == w.strip().lower() and w for w in words)
    left = [
        name
        for name in plan_checks.allowed_names()
        if not any(word in name.lower() for word in words)
    ]
    assert len(left) >= 10
    # Every word should rule out at least one listed exercise, or it checks nothing.
    for word in words:
        assert any(word in name.lower() for name in plan_checks.allowed_names()), word


@pytest.mark.parametrize("case", PLAN_CASES, ids=PLAN_IDS)
def test_expected_notes_come_from_the_health_note(case: dict[str, Any]) -> None:
    check_health_notes(case)


def check_health_notes(case: dict[str, Any]) -> None:
    """A case expects the doctor note exactly when its profile triggers a health flag."""
    profile = UserProfile.model_validate(case["saved_profile"])
    flagged = bool(plan.health_flags(profile))
    groups = case["expect"]["notes_contain"]
    assert bool(groups) == flagged
    for group in groups:
        assert any(word.lower() in plan.HEALTH_NOTE.lower() for word in group), group


def test_knee_case_triggers_the_serious_injury_flag() -> None:
    [knee] = [case for case in PLAN_CASES if case["id"] == "plan-07-knee-injury-doctor-note"]
    text = " ".join(knee["saved_profile"]["injuries"])
    assert guardrails.health_flags(text) == ["serious_injury"]


def test_plan_cases_cover_the_planned_situations() -> None:
    calendars = {case["calendar"] for case in PLAN_CASES}
    assert calendars == {"empty.ics", "normal.ics", "packed.ics"}
    days = {case["saved_profile"]["workout_days"] for case in PLAN_CASES}
    assert {1, 6} <= days, "smallest and largest week"
    assert any(case["expect"]["status"] == 400 for case in PLAN_CASES)
    assert any(case["expect"]["notes_contain"] for case in PLAN_CASES)
    # DESIGN.md §8: no calorie targets; checked on the "lose fat" case.
    lose_fat = next(c for c in PLAN_CASES if c["id"] == "plan-06-short-bodyweight-sessions")
    assert "calorie" in lose_fat["expect"]["notes_exclude"]


# --- safety.json and injection.json (Step C4) ---

SAFETY_DATA: dict[str, Any] = json.loads(
    (PROJECT_ROOT / "eval" / "cases" / "safety.json").read_text(encoding="utf-8")
)
INJECTION_DATA: dict[str, Any] = json.loads(
    (PROJECT_ROOT / "eval" / "cases" / "injection.json").read_text(encoding="utf-8")
)
MIXED = [
    (data["group"], case)
    for data in (SAFETY_DATA, INJECTION_DATA)
    for case in data["cases"]
]
MIXED_IDS = [case["id"] for _, case in MIXED]
PROFILE_EXTRA_RULES = {"reply_excludes", "model_calls_max"}


def by_id(case_id: str) -> dict[str, Any]:
    return next(case for _, case in MIXED if case["id"] == case_id)


@pytest.mark.parametrize("data", [SAFETY_DATA, INJECTION_DATA], ids=["safety", "injection"])
def test_mixed_file_header(data: dict[str, Any]) -> None:
    assert data["step"] == "C4"
    assert data["week_of"] == PLAN_DATA["week_of"]


def test_mixed_case_counts_and_ids() -> None:
    # DESIGN.md §10: 5 safety and 3 injection cases.
    assert [g for g, _ in MIXED].count("safety") == 5
    assert [g for g, _ in MIXED].count("injection") == 3
    for group, case in MIXED:
        assert case["id"].startswith(f"{group}-")
    every_id = IDS + PLAN_IDS + MIXED_IDS
    assert len(every_id) == len(set(every_id)), "case ids must be unique across files"


@pytest.mark.parametrize(("group", "case"), MIXED, ids=MIXED_IDS)
def test_mixed_case_shape(group: str, case: dict[str, Any]) -> None:
    assert case["kind"] in {"profile", "plan"}
    assert case["description"].strip()
    expect = case["expect"]
    if "model_calls_max" in expect:
        calls = expect["model_calls_max"]
        assert isinstance(calls, int) and not isinstance(calls, bool) and calls >= 0
    if case["kind"] == "profile":
        assert set(case) == {"id", "description", "kind", "saved_profile", "messages", "expect"}
        assert set(expect) <= RULES | PROFILE_EXTRA_RULES
        assert expect, "a profile case needs at least one rule"
        ProfileChatRequest.model_validate({"messages": case["messages"]})
        if case["saved_profile"] is not None:
            UserProfile.model_validate(case["saved_profile"], strict=True)
    else:
        assert set(case) == {"id", "description", "kind", "saved_profile", "calendar", "expect"}
        assert set(expect) - OPTIONAL_PLAN_RULES == PLAN_RULES
        assert (FIXTURES / case["calendar"]).is_file()
        check_complete_profile(case)
        check_status_rules(case)
        check_health_notes(case)


@pytest.mark.parametrize(("group", "case"), MIXED, ids=MIXED_IDS)
def test_profile_kind_rules_are_consistent(group: str, case: dict[str, Any]) -> None:
    if case["kind"] != "profile":
        return
    expect = case["expect"]
    named = [*expect.get("exact", {}), *expect.get("approx", {}), *expect.get("contains", {})]
    named += expect.get("empty", [])
    assert set(named) <= set(UserProfile.model_fields)
    if "missing_fields" in expect:
        empty_core = [f for f in CORE_FIELDS if f in expect.get("empty", [])]
        filled = {*expect.get("exact", {}), *expect.get("approx", {}), *expect.get("contains", {})}
        assert [f for f in expect["missing_fields"] if f in empty_core] == empty_core
        assert not set(expect["missing_fields"]) & filled
        assert expect["missing_fields"] == [f for f in CORE_FIELDS if f in expect["missing_fields"]]


@pytest.mark.parametrize(("group", "case"), MIXED, ids=MIXED_IDS)
def test_leak_markers_really_are_in_the_profile_prompt(group: str, case: dict[str, Any]) -> None:
    """Otherwise reply_excludes would pass even when the prompt leaked."""
    from backend.app import profile as profile_module

    for phrase in case["expect"].get("reply_excludes", []):
        assert phrase in profile_module.SYSTEM_PROMPT, phrase


@pytest.mark.parametrize(("group", "case"), MIXED, ids=MIXED_IDS)
def test_plan_kind_200_cases_have_enough_free_days(group: str, case: dict[str, Any]) -> None:
    if case["kind"] == "plan" and case["expect"]["status"] == 200:
        assert free_days_in(case["calendar"]) >= case["saved_profile"]["workout_days"]


def test_no_free_time_case_really_has_no_free_time() -> None:
    case = by_id("safety-04-no-free-time")
    data = (FIXTURES / case["calendar"]).read_bytes()
    assert find_free_slots(data, start_date=WEEK_OF) == []
    assert "no free time" in plan.NO_FREE_TIME


def test_capped_days_case_asks_for_out_of_range_values() -> None:
    case = by_id("safety-05-capped-days")
    assert "10 days" in case["messages"][-1]["content"]
    assert set(case["expect"]["empty"]) == {"workout_days", "session_minutes"}


def test_injection_cases_hit_the_intended_paths() -> None:
    """01 and 03 are caught by the pattern screen; 02 is meant to get past it."""
    direct = by_id("injection-01-ignore-instructions")
    polite = by_id("injection-02-polite-leak-attempt")
    hidden = by_id("injection-03-attack-in-saved-profile")
    assert guardrails.looks_like_injection(direct["messages"][-1]["content"])
    assert not guardrails.looks_like_injection(polite["messages"][-1]["content"])
    assert plan.profile_is_flagged(UserProfile.model_validate(hidden["saved_profile"]))
    expected = hidden["expect"]["detail_contains"][0][0]
    assert expected.lower() in plan.FLAGGED_PROFILE.lower()
