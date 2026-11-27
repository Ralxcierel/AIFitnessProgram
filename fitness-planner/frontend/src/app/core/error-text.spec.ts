import { HttpErrorResponse } from '@angular/common/http';
import { errorText } from './error-text';

describe('errorText', () => {
  it('explains when the back end cannot be reached', () => {
    expect(errorText(new HttpErrorResponse({ status: 0 }))).toContain("Can't reach the back end");
  });

  it('shows error and detail from the back end', () => {
    const err = new HttpErrorResponse({
      status: 400,
      error: { error: 'Request refused', detail: 'Upload your calendar first.' },
    });
    expect(errorText(err)).toBe('Request refused: Upload your calendar first.');
  });

  it('shows only the error when detail is null', () => {
    const err = new HttpErrorResponse({ status: 404, error: { error: 'No plan yet', detail: null } });
    expect(errorText(err)).toBe('No plan yet');
  });

  it('falls back to a general message', () => {
    expect(errorText(new HttpErrorResponse({ status: 500, error: 'oops' }))).toBe(
      'Something went wrong. Please try again.',
    );
    expect(errorText(new Error('x'))).toBe('Something went wrong. Please try again.');
  });
});
