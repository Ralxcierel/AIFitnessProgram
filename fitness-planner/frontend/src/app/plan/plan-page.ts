import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FreeSlot, WeeklyPlan } from '../core/api.types';
import { errorText } from '../core/error-text';
import { PlanService } from './plan.service';

/** Same limit and message as backend/app/guardrails.py and plan.py. */
export const MAX_ICS_BYTES = 200 * 1024;
export const ICS_TOO_LARGE =
  'Request refused: The calendar file is over 200 KB. Please upload a smaller file.';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/**
 * An ISO date or local datetime from the back end as a local Date.
 *
 * The back end sends times with no time zone ("2026-11-23T06:00:00"), meant as
 * local time, so the parts are read directly instead of trusting Date parsing.
 * A time-zone suffix is ignored: plan.py's to_local() never sends one.
 */
export function parseLocal(iso: string): Date {
  const [datePart, timePart = '00:00'] = iso.split('T');
  const [year, month, day] = datePart.split('-').map(Number);
  const [hour, minute] = timePart.split(':').map(Number);
  return new Date(year, month - 1, day, hour, minute);
}

/** "Mon 23 Nov" */
export function dayLabel(iso: string): string {
  const date = parseLocal(iso);
  return `${DAYS[date.getDay()]} ${date.getDate()} ${MONTHS[date.getMonth()]}`;
}

/** "06:00" */
export function timeLabel(iso: string): string {
  const date = parseLocal(iso);
  const hour = String(date.getHours()).padStart(2, '0');
  const minute = String(date.getMinutes()).padStart(2, '0');
  return `${hour}:${minute}`;
}

/** "06:00–09:00" */
export function timeRange(start: string, end: string): string {
  return `${timeLabel(start)}–${timeLabel(end)}`;
}

export interface SlotDay {
  day: string;
  times: string[];
}

/** Free slots grouped by day, in the order the back end sent them. */
export function slotsByDay(slots: FreeSlot[]): SlotDay[] {
  const days: SlotDay[] = [];
  for (const slot of slots) {
    const day = dayLabel(slot.start);
    if (days.at(-1)?.day !== day) days.push({ day, times: [] });
    days.at(-1)!.times.push(timeRange(slot.start, slot.end));
  }
  return days;
}

/** Plan page: upload a calendar, make a weekly plan, see it (Step B4). */
@Component({
  selector: 'app-plan-page',
  templateUrl: './plan-page.html',
  styleUrl: './plan-page.css',
})
export class PlanPage {
  private readonly planService = inject(PlanService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly dayLabel = dayLabel;
  protected readonly timeRange = timeRange;

  /** Free slots from an upload on this visit; null until then. */
  protected readonly slots = signal<FreeSlot[] | null>(null);
  protected readonly slotDays = computed(() => slotsByDay(this.slots() ?? []));
  protected readonly plan = signal<WeeklyPlan | null>(null);

  protected readonly loading = signal(true);
  protected readonly loadError = signal('');
  protected readonly uploading = signal(false);
  protected readonly uploadError = signal('');
  protected readonly planning = signal(false);
  protected readonly planError = signal('');
  /** The result of the last upload or plan, for the status line. */
  private readonly result = signal('');

  /**
   * Text of the one status line, which is always on the page so screen
   * readers announce each change. Work in progress comes before results.
   */
  protected readonly statusText = computed(() => {
    if (this.uploading()) return 'Reading your calendar…';
    if (this.planning()) return 'Making your plan… this can take up to a minute.';
    if (this.loading()) return 'Loading your plan…';
    return this.result();
  });

  /** Set once the user uploads or plans, so a slow first load cannot undo it. */
  private acted = false;

  constructor() {
    this.planService
      .getCurrentPlan()
      .pipe(takeUntilDestroyed())
      .subscribe({
        next: (plan) => {
          if (!this.acted) this.plan.set(plan);
          this.loading.set(false);
        },
        error: (err: unknown) => {
          const noPlanYet = err instanceof HttpErrorResponse && err.status === 404;
          if (!noPlanYet && !this.acted) {
            this.loadError.set(`Couldn't load your plan. ${errorText(err)}`);
          }
          this.loading.set(false);
        },
      });
  }

  protected upload(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    // Clear the field so picking the same (edited) file again fires `change`.
    input.value = '';
    if (!file || this.uploading() || this.planning()) return;
    this.uploadError.set('');
    this.result.set('');
    if (file.size > MAX_ICS_BYTES) {
      this.uploadError.set(ICS_TOO_LARGE);
      return;
    }
    this.startAction();
    this.uploading.set(true);
    this.planService
      .uploadCalendar(file)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.slots.set(response.free_slots);
          // The back end clears the saved plan on a new upload; match it.
          this.plan.set(null);
          this.planError.set('');
          this.result.set(slotSummary(response.free_slots));
          this.uploading.set(false);
        },
        error: (err: unknown) => {
          this.uploadError.set(errorText(err));
          this.uploading.set(false);
        },
      });
  }

  protected makePlan(): void {
    if (this.planning() || this.uploading()) return;
    this.startAction();
    this.planError.set('');
    this.result.set('');
    this.planning.set(true);
    this.planService
      .createPlan()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (plan) => {
          this.plan.set(plan);
          this.result.set('Your plan is ready.');
          this.planning.set(false);
        },
        error: (err: unknown) => {
          this.planError.set(errorText(err));
          this.planning.set(false);
        },
      });
  }

  /** The user acted: a first load still on its way no longer matters. */
  private startAction(): void {
    this.acted = true;
    this.loading.set(false);
    this.loadError.set('');
  }
}

/** "Found 3 free times on 2 days." */
export function slotSummary(slots: FreeSlot[]): string {
  if (!slots.length) return 'No free time of 45 minutes or more was found this week.';
  const days = slotsByDay(slots).length;
  const times = slots.length === 1 ? 'time' : 'times';
  return `Found ${slots.length} free ${times} on ${days} ${days === 1 ? 'day' : 'days'}.`;
}
