import { HttpErrorResponse } from '@angular/common/http';

/**
 * Readable message for a failed request; never repeats what the user typed.
 *
 * Shows the back end's `{error, detail}` body when there is one. The profile and
 * log pages still have their own copy of this (workstream A may switch later).
 */
export function errorText(err: unknown): string {
  if (err instanceof HttpErrorResponse) {
    if (err.status === 0) return "Can't reach the back end. Is it running on port 8000?";
    const body = err.error as { error?: unknown; detail?: unknown } | null;
    if (body && typeof body.error === 'string') {
      return typeof body.detail === 'string' ? `${body.error}: ${body.detail}` : body.error;
    }
  }
  return 'Something went wrong. Please try again.';
}
