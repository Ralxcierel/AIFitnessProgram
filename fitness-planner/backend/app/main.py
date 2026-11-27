"""FastAPI app for the Fitness Planner back end."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from . import plan, profile, workout_log
from .llm import LLMError

app = FastAPI(title="Fitness Planner API")
app.include_router(profile.router)
app.include_router(workout_log.router)
app.include_router(plan.router)


@app.exception_handler(RequestValidationError)
def invalid_request(request: Request, err: RequestValidationError) -> JSONResponse:
    """Report bad input as {error, detail} without echoing what was sent."""
    problems = []
    for item in err.errors():
        where = ".".join(str(part) for part in item["loc"] if part != "body")
        problems.append(f"{where}: {item['msg']}" if where else item["msg"])
    content = {"error": "Invalid request", "detail": "; ".join(problems)}
    return JSONResponse(status_code=422, content=content)


@app.exception_handler(HTTPException)
def http_error(request: Request, err: HTTPException) -> JSONResponse:
    """Report other HTTP errors (400, 404, 405, ...) as {error, detail}."""
    content = {"error": err.detail, "detail": None}
    return JSONResponse(
        status_code=err.status_code, content=content, headers=err.headers
    )


@app.exception_handler(LLMError)
def model_failed(request: Request, err: LLMError) -> JSONResponse:
    """Report a failed model call; LLMError text holds no user data."""
    content = {"error": "The model call failed", "detail": str(err)}
    return JSONResponse(status_code=502, content=content)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Report that the back end is running."""
    return {"status": "ok"}
