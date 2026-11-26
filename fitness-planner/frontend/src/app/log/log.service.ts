import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { LogEntry, PersonalBest } from '../core/api.types';

/** Calls the workout log endpoints (Step A4). */
@Injectable({ providedIn: 'root' })
export class LogService {
  private readonly http = inject(HttpClient);

  /** Saves one entry; the server assigns its id. */
  addEntry(entry: LogEntry): Observable<LogEntry> {
    return this.http.post<LogEntry>('/api/log', entry);
  }

  /** All entries, newest first. */
  getEntries(): Observable<LogEntry[]> {
    return this.http.get<LogEntry[]>('/api/log');
  }

  /** Heaviest weight per exercise, sorted by exercise name. */
  getBests(): Observable<PersonalBest[]> {
    return this.http.get<PersonalBest[]>('/api/log/bests');
  }
}
