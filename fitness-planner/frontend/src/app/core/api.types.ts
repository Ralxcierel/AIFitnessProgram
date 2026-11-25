/**
 * TypeScript mirror of backend/app/schemas.py [contract].
 *
 * Changing this file needs explicit human approval (AGENTS.md section 7).
 * JSON has no date type, so dates and datetimes are ISO 8601 strings.
 */

/** Returned by GET /api/health; this one has no model in schemas.py. */
export interface HealthResponse {
  status: string;
}

export type Experience = 'beginner' | 'intermediate' | 'advanced';

export type ActivityType = 'strength' | 'cardio' | 'mobility';

/** What the user has told us; anything not given is null or empty. */
export interface UserProfile {
  name: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  experience: Experience | null;
  goals: string[];
  workout_days: number | null;
  session_minutes: number | null;
  split_preference: string | null;
  equipment: string[];
  injuries: string[];
  health_notes: string | null;
  dietary_preferences: string[];
  dietary_restrictions: string[];
}

export interface ProfileChatResponse {
  reply: string;
  profile: UserProfile;
  missing_fields: string[];
  refused: boolean;
}

/** start and end are ISO datetimes. */
export interface FreeSlot {
  start: string;
  end: string;
}

export interface Exercise {
  name: string;
  activity_type: ActivityType;
  sets: number;
  reps: number;
}

/** start and end are ISO datetimes. */
export interface Session {
  start: string;
  end: string;
  focus: string;
  exercises: Exercise[];
}

/** week_of is an ISO date (YYYY-MM-DD). */
export interface WeeklyPlan {
  week_of: string;
  sessions: Session[];
  notes: string[];
}

/** date is an ISO date (YYYY-MM-DD). */
export interface LogEntry {
  id: number | null;
  date: string;
  exercise: string;
  sets: number;
  reps: number;
  weight_kg: number | null;
}

/** date is an ISO date (YYYY-MM-DD). */
export interface PersonalBest {
  exercise: string;
  best_weight_kg: number;
  date: string;
}
