"""FastAPI app for the Fitness Planner back end."""

from fastapi import FastAPI

app = FastAPI(title="Fitness Planner API")


@app.get("/api/health")
def health() -> dict[str, str]:
    """Report that the back end is running."""
    return {"status": "ok"}
