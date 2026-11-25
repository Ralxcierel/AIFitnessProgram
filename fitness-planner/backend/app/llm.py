"""The only place that calls the OpenAI API [contract].

call_model() returns a schema-validated object, logs usage metadata (never
prompts or outputs), and can reuse responses during development. Settings come
only from environment variables; see .env.example.
"""

from collections.abc import Sequence
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time
from typing import Literal, TypedDict, TypeVar

import openai
from openai import OpenAI
from pydantic import BaseModel, ValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
USAGE_LOG = PROJECT_ROOT / "logs" / "usage.jsonl"
CACHE_DIR = PROJECT_ROOT / "eval" / "cache"

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class Message(TypedDict):
    """One chat message sent to the model."""

    role: Literal["system", "user", "assistant"]
    content: str


class LLMError(Exception):
    """A model call failed. The text never contains prompts, outputs, or keys."""


def call_model(
    feature: str, messages: Sequence[Message], response_model: type[ResponseT]
) -> ResponseT:
    """Call the model and return its output validated as response_model.

    Raises LLMError if settings are missing, the API fails, the model refuses,
    or the output does not match the schema.
    """
    model = os.environ.get("OPENAI_MODEL", "").strip()
    if not model:
        raise LLMError("OPENAI_MODEL is not set")
    prices = (_price("PRICE_INPUT_PER_1M"), _price("PRICE_OUTPUT_PER_1M"))

    cache_file: Path | None = None
    if os.environ.get("LLM_CACHE", "").strip() == "1":
        cache_file = CACHE_DIR / f"{_cache_key(model, messages, response_model)}.json"
        cached = _read_cache(cache_file, response_model)
        if cached is not None:
            _log_usage(feature, model, 0, 0, 0, 0.0, cached=True, valid=True)
            return cached

    try:
        client = OpenAI()
    except openai.OpenAIError:
        client = None
    if client is None:
        raise LLMError("OpenAI client could not start; is OPENAI_API_KEY set?")

    result: ResponseT | None = None
    error = ""
    raw = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    started = time.perf_counter()
    try:
        # The raw response keeps token counts even when the output is invalid.
        raw = client.responses.with_raw_response.parse(
            model=model,
            input=list(messages),
            text_format=response_model,
            store=False,  # profiles can hold health data
        )
        tokens_in, tokens_out = _token_counts(raw.http_response.json())
        response = raw.parse()
        if response.status == "completed":
            result = response.output_parsed
        if result is None:
            error = f"Model gave no usable output (status: {response.status})"
    except ValidationError:
        error = f"Model output did not match {response_model.__name__}"
    except openai.APIError as err:
        # The full message can echo input or part of the key, so leave it out.
        status = getattr(err, "status_code", None)
        error = (
            f"OpenAI call failed: {type(err).__name__}, "
            f"status={status}, code={err.code}"
        )
    except (ValueError, TypeError, AttributeError):
        if raw is None:
            error = "Request could not be sent; check OPENAI_API_KEY and settings"
        else:
            error = "OpenAI returned an unreadable response"
    latency_ms = round((time.perf_counter() - started) * 1000)

    _log_usage(
        feature,
        model,
        tokens_in,
        tokens_out,
        latency_ms,
        _cost(tokens_in, tokens_out, prices),
        cached=False,
        valid=result is not None,
    )
    if result is None:
        # Raised outside the except blocks so the original error, which can
        # contain user data, is not attached to the traceback.
        raise LLMError(error)
    if cache_file is not None:
        _write_cache(cache_file, result)
    return result


def _token_counts(body: object) -> tuple[int | None, int | None]:
    """Read input and output token counts; None means unknown."""
    if not isinstance(body, dict):
        raise ValueError("response body is not an object")
    usage = body.get("usage")
    if not isinstance(usage, dict):
        return None, None
    tokens_in, tokens_out = usage.get("input_tokens"), usage.get("output_tokens")
    return (
        tokens_in if isinstance(tokens_in, int) else None,
        tokens_out if isinstance(tokens_out, int) else None,
    )


def _price(name: str) -> float | None:
    """Read a price per 1M tokens; blank means unknown."""
    text = os.environ.get(name, "").strip()
    if not text:
        return None
    try:
        price = float(text)
    except ValueError:
        price = -1.0
    if not math.isfinite(price) or price < 0:
        raise LLMError(f"{name} must be a non-negative number")
    return price


def _cost(
    tokens_in: int | None,
    tokens_out: int | None,
    prices: tuple[float | None, float | None],
) -> float | None:
    """Cost in USD, or None when a token count or price is unknown."""
    price_in, price_out = prices
    if tokens_in is None or tokens_out is None or price_in is None or price_out is None:
        return None
    return round((tokens_in * price_in + tokens_out * price_out) / 1_000_000, 8)


def _log_usage(
    feature: str,
    model: str,
    tokens_in: int | None,
    tokens_out: int | None,
    latency_ms: int,
    cost_usd: float | None,
    *,
    cached: bool,
    valid: bool,
) -> None:
    """Append one line of metadata to the usage log."""
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "feature": feature,
        "model": model,
        "input_tokens": tokens_in,
        "output_tokens": tokens_out,
        "latency_ms": latency_ms,
        "cost_usd": cost_usd,
        "cached": cached,
        "valid": valid,
    }
    USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(USAGE_LOG, "a", encoding="utf-8") as log:
        log.write(json.dumps(entry) + "\n")


def _cache_key(
    model: str, messages: Sequence[Message], response_model: type[BaseModel]
) -> str:
    """Hash everything that decides the answer."""
    parts = [model, list(messages), response_model.model_json_schema()]
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()


def _read_cache(path: Path, response_model: type[ResponseT]) -> ResponseT | None:
    """Return the cached response, or None if it is missing or unreadable."""
    try:
        return response_model.model_validate_json(path.read_bytes())
    except (OSError, ValidationError):
        return None


def _write_cache(path: Path, result: BaseModel) -> None:
    """Save a valid response for reuse; a failed save must not lose the result."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.model_dump_json(), encoding="utf-8")
    except OSError:
        pass
