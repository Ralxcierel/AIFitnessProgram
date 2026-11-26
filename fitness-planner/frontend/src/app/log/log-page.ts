import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  AbstractControl,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import { Subject, catchError, forkJoin, map, of, startWith, switchMap } from 'rxjs';
import { LogEntry, PersonalBest } from '../core/api.types';
import { LogService } from './log.service';

/** Same limits as in backend/app/workout_log.py. */
export const MAX_EXERCISE_LENGTH = 100;
export const MAX_SETS_OR_REPS = 1000;
export const MAX_WEIGHT_KG = 1000;

/** Today's date in the user's time zone, as YYYY-MM-DD. */
export function today(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}

/** A whole number from min to max (empty is handled by `required`). */
function wholeFrom(min: number, max: number): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const value = control.value as number | null;
    if (value === null) return null;
    return Number.isInteger(value) && value >= min && value <= max ? null : { range: true };
  };
}

/** Empty, or a number from 0 to MAX_WEIGHT_KG. */
function optionalWeight(control: AbstractControl): ValidationErrors | null {
  const value = control.value as number | null;
  return value === null || (value >= 0 && value <= MAX_WEIGHT_KG) ? null : { range: true };
}

/** Not blank after trimming, and at most MAX_EXERCISE_LENGTH characters. */
function exerciseName(control: AbstractControl): ValidationErrors | null {
  const name = (control.value as string).trim();
  if (!name) return { required: true };
  return name.length <= MAX_EXERCISE_LENGTH ? null : { tooLong: true };
}

/** Readable message for a failed request; never repeats what the user typed. */
function errorText(err: unknown): string {
  if (err instanceof HttpErrorResponse) {
    if (err.status === 0) return "Can't reach the back end. Is it running on port 8000?";
    const body = err.error as { error?: unknown; detail?: unknown } | null;
    if (body && typeof body.error === 'string') {
      return typeof body.detail === 'string' ? `${body.error}: ${body.detail}` : body.error;
    }
  }
  return 'Something went wrong. Please try again.';
}

/** Workout log page: add entries, see them, and see personal bests (Step A4). */
@Component({
  selector: 'app-log-page',
  imports: [ReactiveFormsModule],
  templateUrl: './log-page.html',
  styleUrl: './log-page.css',
})
export class LogPage {
  private readonly log = inject(LogService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly maxLength = MAX_EXERCISE_LENGTH;

  protected readonly form = new FormGroup({
    date: new FormControl(today(), { nonNullable: true, validators: Validators.required }),
    exercise: new FormControl('', { nonNullable: true, validators: exerciseName }),
    sets: new FormControl<number | null>(null, [
      Validators.required,
      wholeFrom(1, MAX_SETS_OR_REPS),
    ]),
    reps: new FormControl<number | null>(null, [
      Validators.required,
      wholeFrom(1, MAX_SETS_OR_REPS),
    ]),
    weight_kg: new FormControl<number | null>(null, optionalWeight),
  });

  /** Each push reloads the log; a newer reload cancels an older one. */
  private readonly reload = new Subject<void>();

  protected readonly entries = signal<LogEntry[]>([]);
  protected readonly bests = signal<PersonalBest[]>([]);
  protected readonly loading = signal(true);
  protected readonly loadError = signal('');
  protected readonly adding = signal(false);
  protected readonly addMessage = signal('');
  protected readonly addError = signal('');

  constructor() {
    // Old results no longer apply once the form changes.
    this.form.valueChanges.pipe(takeUntilDestroyed()).subscribe(() => {
      this.addMessage.set('');
      this.addError.set('');
    });
    this.reload
      .pipe(
        startWith(undefined),
        switchMap(() =>
          forkJoin({ entries: this.log.getEntries(), bests: this.log.getBests() }).pipe(
            map((loaded) => ({ ...loaded, error: null as unknown })),
            catchError((error: unknown) => of({ entries: null, bests: null, error })),
          ),
        ),
        takeUntilDestroyed(),
      )
      .subscribe(({ entries, bests, error }) => {
        if (entries && bests) {
          this.entries.set(entries);
          this.bests.set(bests);
          this.loadError.set('');
        } else {
          this.loadError.set(`Couldn't load your workout log. ${errorText(error)}`);
        }
        this.loading.set(false);
      });
  }

  protected add(): void {
    if (this.adding()) return;
    this.addMessage.set('');
    this.addError.set('');
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.addError.set('Please fix the highlighted fields first.');
      return;
    }
    const value = this.form.getRawValue();
    const entry: LogEntry = {
      id: null,
      date: value.date,
      exercise: value.exercise.trim(),
      sets: value.sets as number,
      reps: value.reps as number,
      weight_kg: value.weight_kg,
    };
    this.adding.set(true);
    this.log
      .addEntry(entry)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (saved) => {
          // Keep the date and exercise for the next set; clear the numbers.
          this.form.reset({ date: value.date, exercise: saved.exercise });
          this.addMessage.set(`Logged ${saved.exercise}.`);
          this.adding.set(false);
          this.reload.next();
        },
        error: (err: unknown) => {
          this.addError.set(errorText(err));
          this.adding.set(false);
        },
      });
  }

  /** True when a field is invalid and the user has touched it. */
  protected showError(field: keyof typeof this.form.controls): boolean {
    const control = this.form.controls[field];
    return control.invalid && control.touched;
  }

  /** The id of a field's error message while it is shown, for screen readers. */
  protected errorId(field: keyof typeof this.form.controls): string | null {
    return this.showError(field) ? `${field}-error` : null;
  }
}
