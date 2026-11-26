"""Offline checks that eval/cases/profile.json is well-formed (Step A5).

These tests only read the case file; nothing here calls the API. The matching
rules are described in eval/cases/README.md.
"""

import json
from pathlib import Path
import sys
from typing import Any

import pytest

# Ensure fitness-planner root is on sys.path regardless of execution directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.profile import CORE_FIELDS, ProfileChatRequest
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
