import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { CalendarResponse, WeeklyPlan } from '../core/api.types';
import { PlanService } from './plan.service';

const PLAN: WeeklyPlan = { week_of: '2026-11-23', sessions: [], notes: [] };

describe('PlanService', () => {
  let service: PlanService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(PlanService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('uploads the calendar as a form field named "file"', () => {
    const file = new File(['BEGIN:VCALENDAR'], 'week.ics', { type: 'text/calendar' });
    const reply: CalendarResponse = {
      free_slots: [{ start: '2026-11-23T06:00:00', end: '2026-11-23T09:00:00' }],
    };
    let result: CalendarResponse | undefined;
    service.uploadCalendar(file).subscribe((received) => (result = received));
    const request = http.expectOne('/api/calendar');
    request.flush(reply);

    expect(request.request.method).toBe('POST');
    const body = request.request.body as FormData;
    expect(body.get('file')).toBeInstanceOf(File);
    expect((body.get('file') as File).name).toBe('week.ics');
    expect(result).toEqual(reply);
  });

  it('asks for a new plan', () => {
    let result: WeeklyPlan | undefined;
    service.createPlan().subscribe((received) => (result = received));
    const request = http.expectOne('/api/plan');
    request.flush(PLAN);

    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({});
    expect(result).toEqual(PLAN);
  });

  it('gets the current plan', () => {
    let result: WeeklyPlan | undefined;
    service.getCurrentPlan().subscribe((received) => (result = received));
    const request = http.expectOne('/api/plan/current');
    request.flush(PLAN);

    expect(request.request.method).toBe('GET');
    expect(result).toEqual(PLAN);
  });
});
