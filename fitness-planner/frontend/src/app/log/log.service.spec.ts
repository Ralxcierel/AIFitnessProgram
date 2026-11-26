import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { LogEntry, PersonalBest } from '../core/api.types';
import { LogService } from './log.service';

const ENTRY: LogEntry = {
  id: null,
  date: '2026-11-20',
  exercise: 'Squat',
  sets: 3,
  reps: 5,
  weight_kg: 60,
};

describe('LogService', () => {
  let service: LogService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(LogService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('posts a new entry', () => {
    let result: LogEntry | undefined;
    service.addEntry(ENTRY).subscribe((saved) => (result = saved));
    const request = http.expectOne('/api/log');
    request.flush({ ...ENTRY, id: 1 });

    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(ENTRY);
    expect(result).toEqual({ ...ENTRY, id: 1 });
  });

  it('gets the entries', () => {
    let result: LogEntry[] | undefined;
    service.getEntries().subscribe((entries) => (result = entries));
    const request = http.expectOne('/api/log');
    request.flush([{ ...ENTRY, id: 1 }]);

    expect(request.request.method).toBe('GET');
    expect(result).toEqual([{ ...ENTRY, id: 1 }]);
  });

  it('gets the personal bests', () => {
    const bests: PersonalBest[] = [
      { exercise: 'Squat', best_weight_kg: 60, date: '2026-11-20' },
    ];
    let result: PersonalBest[] | undefined;
    service.getBests().subscribe((received) => (result = received));
    const request = http.expectOne('/api/log/bests');
    request.flush(bests);

    expect(request.request.method).toBe('GET');
    expect(result).toEqual(bests);
  });
});
