import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { CalendarResponse, WeeklyPlan } from '../core/api.types';

/** Calls the calendar and plan endpoints (Steps B2, B4). */
@Injectable({ providedIn: 'root' })
export class PlanService {
  private readonly http = inject(HttpClient);

  /** Uploads an .ics file; the server saves and returns the free slots. */
  uploadCalendar(file: File): Observable<CalendarResponse> {
    const form = new FormData();
    form.append('file', file, file.name);
    return this.http.post<CalendarResponse>('/api/calendar', form);
  }

  /** Makes a new plan for the uploaded calendar's week and saves it. */
  createPlan(): Observable<WeeklyPlan> {
    return this.http.post<WeeklyPlan>('/api/plan', {});
  }

  /** The saved plan; fails with 404 when there is none yet. */
  getCurrentPlan(): Observable<WeeklyPlan> {
    return this.http.get<WeeklyPlan>('/api/plan/current');
  }
}
