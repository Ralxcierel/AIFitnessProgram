"""Offline unit tests for the profile chat (Step A1). Nothing here calls the API."""

from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest

# Ensure fitness-planner root is on sys.path regardless of execution directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import main, profile
from backend.app.llm import LLMError
from backend.app.schemas import ProfileChatResponse, UserProfile

URL = "/api/profile/chat"
CHAT = [
    {"role": "user", "content": "I'm Sam Sample, 180 cm"},
    {"role": "assistant", "content": "Thanks! What is your weight?"},
    {"role": "user", "content": "80 kg"},
]
FULL_CORE = {
    "height_cm": 180,
    "weight_kg": 80,
    "experience": "beginner",
    "goals": ["get stronger"],
    "workout_days": 3,
    "session_minutes": 45,
}


class FakeModel:
    """Stands in for call_model() and records each call."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.error: LLMError | None = None
        self.response = ProfileChatResponse(
            reply="How many days a week?",
            profile=UserProfile(name="Sam Sample", height_cm=180, weight_kg=80),
            missing_fields=["injuries"],  # wrong on purpose; Python decides
        )

    def __call__(self, feature, messages, response_model) -> ProfileChatResponse:
        self.calls.append((feature, messages, response_model))
        if self.error:
            raise self.error
        return self.response


@pytest.fixture
def model(monkeypatch: pytest.MonkeyPatch) -> FakeModel:
    fake = FakeModel()
    monkeypatch.setattr(profile, "call_model", fake)
    return fake


@pytest.fixture
def client() -> TestClient:
    return TestClient(main.app)


def test_chat_returns_valid_response_with_missing_fields(
    model: FakeModel, client: TestClient
) -> None:
    result = client.post(URL, json={"messages": CHAT})
    assert result.status_code == 200
    body = ProfileChatResponse.model_validate(result.json())
    assert body.reply == "How many days a week?"
    assert body.profile == model.response.profile
    assert body.refused is False
    assert body.missing_fields == [
        "experience",
        "goals",
        "workout_days",
        "session_minutes",
    ]


def test_model_gets_prompt_then_whole_chat(
    model: FakeModel, client: TestClient
) -> None:
    client.post(URL, json={"messages": CHAT})
    system = {"role": "system", "content": profile.SYSTEM_PROMPT}
    assert model.calls == [("profile", [system, *CHAT], ProfileChatResponse)]


def test_prompt_names_every_core_field() -> None:
    for field in profile.CORE_FIELDS:
        assert field in profile.SYSTEM_PROMPT


def test_core_fields_exist_in_the_schema() -> None:
    assert set(profile.CORE_FIELDS) <= set(UserProfile.model_fields)


def test_empty_profile_is_missing_every_core_field() -> None:
    assert profile.missing_fields(UserProfile()) == list(profile.CORE_FIELDS)


def test_optional_fields_never_count_as_missing() -> None:
    assert profile.missing_fields(UserProfile(**FULL_CORE)) == []


@pytest.mark.parametrize("field", FULL_CORE)
def test_each_core_field_is_reported(field: str) -> None:
    rest = {key: value for key, value in FULL_CORE.items() if key != field}
    assert profile.missing_fields(UserProfile(**rest)) == [field]


@pytest.mark.parametrize(
    "body, where",
    [
        ({}, "messages"),
        ({"messages": []}, "messages"),
        ({"messages": [{"role": "user", "content": ""}]}, "messages.0.content"),
        ({"messages": [{"role": "user"}]}, "messages.0.content"),
        ({"messages": [{"role": "system", "content": "SECRET"}]}, "messages.0.role"),
        ({"messages": [{"role": "user", "content": ["SECRET"]}]}, "messages.0.content"),
        ({"messages": [{"role": "assistant", "content": "SECRET"}]}, "last message"),
    ],
)
def test_bad_requests_use_the_shared_error_format(
    model: FakeModel, client: TestClient, body: dict, where: str
) -> None:
    result = client.post(URL, json=body)
    assert result.status_code == 422
    assert set(result.json()) == {"error", "detail"}
    assert result.json()["error"] == "Invalid request"
    assert where in result.json()["detail"]
    assert "SECRET" not in result.text
    assert model.calls == []


def test_unreadable_json_uses_the_shared_error_format(
    model: FakeModel, client: TestClient
) -> None:
    result = client.post(
        URL, content="{SECRET", headers={"content-type": "application/json"}
    )
    assert result.status_code == 422
    assert set(result.json()) == {"error", "detail"}
    assert "SECRET" not in result.text


@pytest.mark.parametrize(
    "content", [b'{"messages": "\xff"}', b"[" * 100_000], ids=["not-utf8", "too-deep"]
)
def test_undecodable_body_uses_the_shared_error_format(
    model: FakeModel, client: TestClient, content: bytes
) -> None:
    result = client.post(
        URL, content=content, headers={"content-type": "application/json"}
    )
    assert result.status_code in (400, 422)
    assert set(result.json()) == {"error", "detail"}
    assert model.calls == []


def test_unknown_path_and_wrong_method_use_the_shared_error_format(
    client: TestClient,
) -> None:
    missing = client.get("/api/no-such-path")
    assert missing.status_code == 404
    assert missing.json() == {"error": "Not Found", "detail": None}
    wrong = client.get(URL)
    assert wrong.status_code == 405
    assert wrong.json() == {"error": "Method Not Allowed", "detail": None}
    assert wrong.headers["allow"] == "POST"


def test_model_failure_is_a_502(model: FakeModel, client: TestClient) -> None:
    model.error = LLMError("Model output did not match ProfileChatResponse")
    result = client.post(URL, json={"messages": CHAT})
    assert result.status_code == 502
    assert result.json() == {
        "error": "The model call failed",
        "detail": "Model output did not match ProfileChatResponse",
    }


def test_health_still_works(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}
