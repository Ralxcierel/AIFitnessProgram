# Evaluation cases

Test cases for `eval/run_eval.py` (step C4). One JSON file per group (DESIGN.md §10):

| File | Group | Step | Status |
|---|---|---|---|
| `profile.json` | Profile extraction, 9 cases (DESIGN.md §10 asks for 8; a 9th "vague answers" case was added) | A5 | Written; not run yet (needs the C4 harness and an API key) |
| `plan.json` | Plan generation, 8 cases | B5 | Not written yet |

**All cases use synthetic personas only.** Never put real personal data here (AGENTS.md §9).

`backend/tests/test_eval_cases.py` checks offline that `profile.json` is well-formed. Run it after every edit.

## Profile case format (`profile.json`)

```json
{
  "group": "profile",
  "step": "A5",
  "endpoint": "POST /api/profile/chat",
  "cases": [
    {
      "id": "profile-01-all-in-one-metric",
      "description": "One line on what this case tests.",
      "saved_profile": null,
      "messages": [{ "role": "user", "content": "..." }],
      "expect": {
        "refused": false,
        "exact": { "experience": "beginner", "workout_days": 3 },
        "approx": { "height_cm": { "value": 172, "tolerance": 1 } },
        "contains": { "goals": [["strength", "stronger"]] },
        "empty": ["injuries"],
        "missing_fields": []
      }
    }
  ]
}
```

| Key | Meaning |
|---|---|
| `id` | Unique, stable name. Used in the results report. |
| `saved_profile` | `null` for no saved profile, or a `UserProfile` (missing keys = empty). The harness saves it before the chat, using a fresh throwaway database for every case: point `backend.app.db.DB_PATH` at a new temp file per case (as `backend/tests/test_profile.py` does), then call `db.save_profile(...)` if `saved_profile` is not `null`. |
| `messages` | The chat sent as the body of `POST /api/profile/chat`. It must end with a `user` message. |
| `expect` | What the returned `ProfileChatResponse` must contain (rules below). Fields not named in any rule are not scored. |

## Matching rules

Each rule below is one **check**. The field names are `UserProfile` fields.

| Rule | Passes when |
|---|---|
| `refused` | `response.refused` equals this value. |
| `exact` | The profile field equals the value exactly. Used for `experience` and whole numbers. |
| `approx` | The field is a number within `value ± tolerance`. Used for cm and kg, where unit conversion and rounding vary. |
| `contains` | For each group of keywords, at least one keyword appears in the field (case-insensitive substring; list fields are joined with spaces). One check per group. Example: `[["strength", "stronger"]]` = one check, "mentions strength or stronger". |
| `empty` | The field is `null` (single values) or `[]` (lists). This catches the model guessing values the user never gave. One check per field. |
| `missing_fields` | `response.missing_fields` equals this list exactly, in order. |

Details for the scorer:

- Compare values **after** parsing the response into `ProfileChatResponse`, so `3` and `3.0` are equal for whole-number fields.
- `exact`, `approx` and `contains` **fail** when the field is `null` or `[]`.
- `missing_fields` is computed in Python from the returned profile, so it repeats the `empty` checks for core fields. Keep it in the field-match rate (one check per case), and note in the report that a missed core field costs two checks.
- A model answer with a value outside the schema's range (for example `workout_days: 7` in `profile-06`) fails validation, so that case counts as **not schema-valid** and scores 0 on all its checks. That is the intended result.

## Metrics (DESIGN.md §10)

- **Schema-valid rate:** share of cases where the endpoint returned HTTP 200 with a valid `ProfileChatResponse`. A case that fails here scores 0 on every check.
- **Field-match rate:** checks passed ÷ checks total, over all cases. Also report it per case.
- Also record per case (from `logs/usage.jsonl`): tokens, latency, cost.

The **baseline** run (DESIGN.md §10) uses the same cases and the same scoring, with a naive single prompt instead of the full pipeline.
