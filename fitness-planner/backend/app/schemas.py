"""Shared Pydantic models for the Fitness Planner API [contract].

Mirrors docs/DESIGN.md section 6. Changing this file needs explicit human
approval (AGENTS.md section 7); keep frontend/src/app/core/api.types.ts in step.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """What the user has told us; anything not given stays None or empty."""

    name: str | None = None
    height_cm: float | None = Field(None, gt=100, lt=250)
    weight_kg: float | None = Field(None, gt=30, lt=300)
    experience: Literal["beginner", "intermediate", "advanced"] | None = None
    goals: list[str] = []
    workout_days: int | None = Field(None, ge=1, le=6)
    session_minutes: int | None = Field(None, ge=15, le=120)
    split_preference: str | None = None
    equipment: list[str] = []
    injuries: list[str] = []  # basic, user-stated
    health_notes: str | None = None  # basic, user-stated
    dietary_preferences: list[str] = []
    dietary_restrictions: list[str] = []  # incl. allergies


class ProfileChatResponse(BaseModel):
    """Reply from the profile chat, with the profile so far."""

    reply: str
    profile: UserProfile
    missing_fields: list[str]
    refused: bool = False


class FreeSlot(BaseModel):
    """A free time window suitable for scheduling a workout."""

    start: datetime
    end: datetime


class Exercise(BaseModel):
    """One exercise prescription."""

    name: str  # must be in exercises.json
    activity_type: Literal["strength", "cardio", "mobility"]
    sets: int = Field(ge=1, le=6)
    reps: int = Field(ge=1, le=30)


class Session(BaseModel):
    """One scheduled workout."""

    start: datetime
    end: datetime
    focus: str
    exercises: list[Exercise] = Field(min_length=1)


class WeeklyPlan(BaseModel):
    """A one-week workout plan."""

    week_of: date
    sessions: list[Session]
    notes: list[str] = []  # e.g. "check with a physical therapist about your knee"


class LogEntry(BaseModel):
    """One logged exercise."""

    id: int | None = None
    date: date
    exercise: str
    sets: int = Field(ge=1)
    reps: int = Field(ge=1)
    weight_kg: float | None = Field(None, ge=0)


class PersonalBest(BaseModel):
    """Heaviest logged weight for an exercise, computed in Python."""

    exercise: str
    best_weight_kg: float
    date: date
