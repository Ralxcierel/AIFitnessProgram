"""Offline unit tests for call_model() (Step C1). Nothing here calls the API."""

import json
from pathlib import Path
import sys
from types import SimpleNamespace

import openai
import pytest
from pydantic import BaseModel

# Ensure fitness-planner root is on sys.path regardless of execution directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import llm


class Answer(BaseModel):
    text: str
    score: int


class OtherAnswer(BaseModel):
    text: str
    score: int
    extra: str = ""


MESSAGES = [{"role": "user", "content": "SECRET PROMPT"}]
GOOD = '{"text": "SECRET OUTPUT", "score": 3}'
BAD = '{"text": "SECRET OUTPUT", "score": "SECRET BAD VALUE"}'
LOG_KEYS = {
    "ts",
    "feature",
    "model",
    "input_tokens",
    "output_tokens",
    "latency_ms",
    "cost_usd",
    "cached",
    "valid",
}


class FakeAPI:
    """Stands in for the OpenAI client and records each request."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.output: str | None = GOOD  # None means the model refused
        self.status = "completed"
        self.error: Exception | None = None  # raised while sending
        self.parse_error: Exception | None = None  # raised while reading
        self.body: object = {"usage": {"input_tokens": 1000, "output_tokens": 500}}
        self.responses = SimpleNamespace(
            with_raw_response=SimpleNamespace(parse=self._parse)
        )

    def _parse(self, **kwargs) -> SimpleNamespace:
        self.calls.append(kwargs)
        if self.error:
            raise self.error

        def parse() -> SimpleNamespace:
            if self.parse_error:
                raise self.parse_error
            parsed = None
            if self.output is not None:
                parsed = kwargs["text_format"].model_validate_json(self.output)
            return SimpleNamespace(status=self.status, output_parsed=parsed)

        http_response = SimpleNamespace(json=lambda: self.body)
        return SimpleNamespace(http_response=http_response, parse=parse)


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeAPI:
    fake = FakeAPI()
    monkeypatch.setattr(llm, "OpenAI", lambda: fake)
    monkeypatch.setattr(llm, "USAGE_LOG", tmp_path / "logs" / "usage.jsonl")
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("PRICE_INPUT_PER_1M", "2")
    monkeypatch.setenv("PRICE_OUTPUT_PER_1M", "4")
    monkeypatch.setenv("LLM_CACHE", "0")
    return fake


def log_lines() -> list[dict]:
    return [json.loads(line) for line in llm.USAGE_LOG.read_text().splitlines()]


def ask(model: type[BaseModel] = Answer) -> BaseModel:
    return llm.call_model("test", MESSAGES, model)


def test_returns_validated_object_and_logs_usage(api: FakeAPI) -> None:
    assert ask() == Answer(text="SECRET OUTPUT", score=3)
    [entry] = log_lines()
    assert set(entry) == LOG_KEYS
    assert entry["feature"] == "test"
    assert entry["model"] == "test-model"
    assert (entry["input_tokens"], entry["output_tokens"]) == (1000, 500)
    assert entry["cost_usd"] == pytest.approx(0.004)
    assert (entry["cached"], entry["valid"]) == (False, True)


def test_request_contents(api: FakeAPI) -> None:
    ask()
    assert api.calls == [
        {
            "model": "test-model",
            "input": MESSAGES,
            "text_format": Answer,
            "store": False,
        }
    ]


def test_log_has_no_prompt_or_output(api: FakeAPI) -> None:
    ask()
    assert "SECRET" not in llm.USAGE_LOG.read_text()


def test_invalid_output_is_logged_with_tokens_and_hidden(api: FakeAPI) -> None:
    api.output = BAD
    with pytest.raises(llm.LLMError) as caught:
        ask()
    assert str(caught.value) == "Model output did not match Answer"
    assert caught.value.__context__ is None
    [entry] = log_lines()
    assert entry["valid"] is False
    assert entry["input_tokens"] == 1000
    assert entry["cost_usd"] == pytest.approx(0.004)


def test_refusal_raises(api: FakeAPI) -> None:
    api.output = None
    with pytest.raises(llm.LLMError, match="no usable output"):
        ask()
    assert log_lines()[0]["valid"] is False


def test_incomplete_response_raises(api: FakeAPI) -> None:
    api.status = "incomplete"
    with pytest.raises(llm.LLMError, match="incomplete"):
        ask()
    assert log_lines()[0]["valid"] is False


def test_api_error_is_logged_without_its_message(api: FakeAPI) -> None:
    request = SimpleNamespace(headers={})
    api.error = openai.APIError("SECRET", request=request, body=None)
    with pytest.raises(llm.LLMError, match="OpenAI call failed") as caught:
        ask()
    assert "SECRET" not in str(caught.value)
    assert caught.value.__context__ is None
    [entry] = log_lines()
    assert entry["valid"] is False
    assert entry["input_tokens"] is None
    assert entry["cost_usd"] is None


@pytest.mark.parametrize("body", [[], None])
def test_non_object_response_is_logged(api: FakeAPI, body: object) -> None:
    api.body = body
    with pytest.raises(llm.LLMError, match="unreadable"):
        ask()
    assert log_lines()[0]["valid"] is False


@pytest.mark.parametrize("kind", [ValueError, TypeError, AttributeError])
def test_unreadable_response_is_logged(
    api: FakeAPI, kind: type[Exception]
) -> None:
    api.parse_error = kind("SECRET")
    with pytest.raises(llm.LLMError, match="unreadable") as caught:
        ask()
    assert caught.value.__context__ is None
    assert log_lines()[0]["valid"] is False


@pytest.mark.parametrize(
    "body",
    [{}, {"usage": None}, {"usage": {"input_tokens": "x", "output_tokens": "x"}}],
)
def test_missing_usage_is_unknown_not_zero(api: FakeAPI, body: object) -> None:
    api.body = body
    ask()
    [entry] = log_lines()
    assert entry["output_tokens"] is None
    assert entry["cost_usd"] is None


@pytest.mark.parametrize("name", ["PRICE_INPUT_PER_1M", "PRICE_OUTPUT_PER_1M"])
def test_blank_price_gives_unknown_cost(
    api: FakeAPI, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.setenv(name, "")
    ask()
    assert log_lines()[0]["cost_usd"] is None


@pytest.mark.parametrize("value", ["abc", "-1", "nan", "inf"])
def test_bad_price_stops_before_spending(
    api: FakeAPI, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("PRICE_INPUT_PER_1M", value)
    with pytest.raises(llm.LLMError, match="PRICE_INPUT_PER_1M"):
        ask()
    assert api.calls == []


def test_unsendable_request_points_at_settings(api: FakeAPI) -> None:
    api.error = UnicodeEncodeError("ascii", "SECRET", 0, 1, "bad key")
    with pytest.raises(llm.LLMError, match="check OPENAI_API_KEY") as caught:
        ask()
    assert "SECRET" not in str(caught.value)
    assert caught.value.__context__ is None


@pytest.mark.parametrize("value", ["", "  "])
def test_missing_model_setting(
    api: FakeAPI, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("OPENAI_MODEL", value)
    with pytest.raises(llm.LLMError, match="OPENAI_MODEL"):
        ask()
    assert api.calls == []


def test_missing_key(api: FakeAPI, monkeypatch: pytest.MonkeyPatch) -> None:
    def no_key() -> None:
        raise openai.OpenAIError("no key")

    monkeypatch.setattr(llm, "OpenAI", no_key)
    with pytest.raises(llm.LLMError, match="OPENAI_API_KEY") as caught:
        ask()
    assert caught.value.__context__ is None
    assert not llm.USAGE_LOG.exists()


def test_cache_reuses_response_at_no_cost(
    api: FakeAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_CACHE", "1")
    assert ask() == ask()
    assert len(api.calls) == 1
    first, second = log_lines()
    assert (first["cached"], second["cached"]) == (False, True)
    assert (second["cost_usd"], second["input_tokens"]) == (0, 0)
    assert "SECRET" not in llm.USAGE_LOG.read_text()


def test_cache_off_calls_again(api: FakeAPI) -> None:
    ask()
    ask()
    assert len(api.calls) == 2
    assert not llm.CACHE_DIR.exists()


def test_cache_misses_when_anything_changes(
    api: FakeAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_CACHE", "1")
    ask()
    ask(OtherAnswer)
    llm.call_model("test", [{"role": "user", "content": "different"}], Answer)
    monkeypatch.setenv("OPENAI_MODEL", "other-model")
    ask()
    assert len(api.calls) == 4


def test_failures_are_not_cached(
    api: FakeAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_CACHE", "1")
    api.output = BAD
    with pytest.raises(llm.LLMError):
        ask()
    api.output = GOOD
    ask()
    assert len(api.calls) == 2


def test_failed_cache_write_keeps_result(
    api: FakeAPI, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("")
    monkeypatch.setattr(llm, "CACHE_DIR", blocker)
    monkeypatch.setenv("LLM_CACHE", "1")
    assert ask() == Answer(text="SECRET OUTPUT", score=3)


def test_damaged_cache_file_is_ignored(
    api: FakeAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_CACHE", "1")
    ask()
    [cached] = llm.CACHE_DIR.iterdir()
    cached.write_text("not json")
    ask()
    assert len(api.calls) == 2
