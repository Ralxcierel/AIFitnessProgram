import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FreeSlot, WeeklyPlan } from '../core/api.types';
import {
  ICS_TOO_LARGE,
  MAX_ICS_BYTES,
  PlanPage,
  dayLabel,
  parseLocal,
  slotsByDay,
  timeRange,
} from './plan-page';

const SLOTS: FreeSlot[] = [
  { start: '2026-11-23T06:00:00', end: '2026-11-23T09:00:00' },
  { start: '2026-11-23T17:00:00', end: '2026-11-23T22:00:00' },
  { start: '2026-11-24T06:00:00', end: '2026-11-24T09:00:00' },
];

const PLAN: WeeklyPlan = {
  week_of: '2026-11-23',
  sessions: [
    {
      start: '2026-11-23T06:00:00',
      end: '2026-11-23T06:45:00',
      focus: 'Full body',
      exercises: [
        { name: 'Goblet squat', activity_type: 'strength', sets: 3, reps: 10 },
        { name: 'Brisk walk', activity_type: 'cardio', sets: 1, reps: 10 },
      ],
    },
    {
      start: '2026-11-25T18:00:00',
      end: '2026-11-25T18:45:00',
      focus: 'Upper body',
      exercises: [{ name: 'Push-up', activity_type: 'strength', sets: 3, reps: 8 }],
    },
  ],
  notes: ['Check with a doctor first.', 'Warm up first.'],
};

describe('plan page helpers', () => {
  it('reads back-end times as local times', () => {
    const date = parseLocal('2026-11-23T06:30:00');
    expect([date.getFullYear(), date.getMonth(), date.getDate()]).toEqual([2026, 10, 23]);
    expect([date.getHours(), date.getMinutes()]).toEqual([6, 30]);
  });

  it('reads a plain date as midnight', () => {
    expect(parseLocal('2026-11-23').getHours()).toBe(0);
  });

  it('formats days and time ranges', () => {
    expect(dayLabel('2026-11-23')).toBe('Mon 23 Nov');
    expect(dayLabel('2026-11-29T21:00:00')).toBe('Sun 29 Nov');
    expect(timeRange('2026-11-23T06:00:00', '2026-11-23T09:05:00')).toBe('06:00–09:05');
  });

  it('groups free slots by day', () => {
    expect(slotsByDay(SLOTS)).toEqual([
      { day: 'Mon 23 Nov', times: ['06:00–09:00', '17:00–22:00'] },
      { day: 'Tue 24 Nov', times: ['06:00–09:00'] },
    ]);
    expect(slotsByDay([])).toEqual([]);
  });
});

describe('PlanPage', () => {
  let fixture: ComponentFixture<PlanPage>;
  let http: HttpTestingController;

  const page = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const text = async (): Promise<string> => {
    await fixture.whenStable();
    return page().textContent ?? '';
  };
  const fileInput = (): HTMLInputElement => page().querySelector('#calendar') as HTMLInputElement;
  const makeButton = (): HTMLButtonElement =>
    page().querySelector('button') as HTMLButtonElement;
  const chooseFile = (file: File): void => {
    Object.defineProperty(fileInput(), 'files', { value: [file], configurable: true });
    fileInput().dispatchEvent(new Event('change'));
  };
  const status = (): string =>
    page().querySelector('[role="status"]')?.textContent?.trim() ?? 'MISSING';
  const alerts = (): string[] =>
    Array.from(page().querySelectorAll('[role="alert"]')).map((a) => a.textContent ?? '');
  const icsFile = (size = 20): File =>
    new File(['x'.repeat(size)], 'week.ics', { type: 'text/calendar' });
  const answerLoad = async (plan: WeeklyPlan | null): Promise<void> => {
    const request = http.expectOne('/api/plan/current');
    if (plan) {
      request.flush(plan);
    } else {
      request.flush({ error: 'No plan yet', detail: null }, { status: 404, statusText: 'Not Found' });
    }
    await fixture.whenStable();
  };
  const refuse = (url: string, detail: string, status = 400): void => {
    http
      .expectOne(url)
      .flush({ error: 'Request refused', detail }, { status, statusText: 'Bad Request' });
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [PlanPage],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(PlanPage);
  });

  afterEach(() => http.verify());

  it('says there is no plan yet when the back end has none', async () => {
    await answerLoad(null);
    const shown = await text();
    expect(shown).toContain('No plan yet. Upload your calendar, then make your plan.');
    expect(page().querySelector('[role="alert"]')).toBeNull();
  });

  it('shows the saved plan on load', async () => {
    await answerLoad(PLAN);
    const shown = await text();
    expect(shown).toContain('Your week of Mon 23 Nov');
    expect(shown).toContain('Check with a doctor first.');
    const headings = Array.from(page().querySelectorAll('.session h3')).map((h) =>
      h.textContent?.replace(/\s+/g, ' ').trim(),
    );
    expect(headings).toEqual([
      'Mon 23 Nov, 06:00–06:45 · Full body',
      'Wed 25 Nov, 18:00–18:45 · Upper body',
    ]);
    const firstRows = Array.from(page().querySelectorAll('.session')[0].querySelectorAll('tbody tr'));
    const cells = firstRows.map((row) =>
      Array.from(row.querySelectorAll('td')).map((cell) => cell.textContent?.trim()),
    );
    expect(cells).toEqual([
      ['Goblet squat', 'strength', '3 × 10'],
      ['Brisk walk', 'cardio', '1 × 10'],
    ]);
  });

  it('shows an error when the plan cannot be loaded', async () => {
    http.expectOne('/api/plan/current').flush(null, { status: 0, statusText: 'Unknown Error' });
    expect(await text()).toContain("Couldn't load your plan. Can't reach the back end.");
  });

  it('uploads a calendar and lists the free times by day', async () => {
    await answerLoad(null);
    chooseFile(icsFile());
    expect(await text()).toContain('Reading your calendar…');
    const request = http.expectOne('/api/calendar');
    expect((request.request.body as FormData).get('file')).toBeInstanceOf(File);
    request.flush({ free_slots: SLOTS });
    const shown = (await text()).replace(/\s+/g, ' ');
    expect(status()).toBe('Found 3 free times on 2 days.');
    expect(shown).toContain('Mon 23 Nov: 06:00–09:00, 17:00–22:00');
    expect(shown).toContain('Tue 24 Nov: 06:00–09:00');
  });

  it('says so when the calendar has no free time', async () => {
    await answerLoad(null);
    chooseFile(icsFile());
    http.expectOne('/api/calendar').flush({ free_slots: [] });
    expect(await text()).toContain('No free time of 45 minutes or more was found this week.');
  });

  it('refuses a file over 200 KB without uploading it', async () => {
    await answerLoad(null);
    chooseFile(icsFile(MAX_ICS_BYTES + 1));
    expect(await text()).toContain(ICS_TOO_LARGE);
    http.expectNone('/api/calendar');
  });

  it('uploads a file of exactly 200 KB', async () => {
    await answerLoad(null);
    chooseFile(icsFile(MAX_ICS_BYTES));
    http.expectOne('/api/calendar').flush({ free_slots: [] });
    await fixture.whenStable();
    expect(alerts()).toEqual([]);
  });

  it('keeps one status line on the page and updates its text', async () => {
    await fixture.whenStable();
    const line = page().querySelector('[role="status"]');
    expect(status()).toBe('Loading your plan…');
    await answerLoad(null);
    expect(status()).toBe('');
    chooseFile(icsFile());
    await fixture.whenStable();
    expect(page().querySelector('[role="status"]')).toBe(line);
    expect(status()).toBe('Reading your calendar…');
    http.expectOne('/api/calendar').flush({ free_slots: SLOTS });
    await fixture.whenStable();
    expect(page().querySelector('[role="status"]')).toBe(line);
    expect(status()).toBe('Found 3 free times on 2 days.');
  });

  it('clears the file field after each upload so the same file can be picked again', async () => {
    await answerLoad(null);
    const cleared: string[] = [];
    Object.defineProperty(fileInput(), 'value', {
      configurable: true,
      get: () => '',
      set: (value: string) => cleared.push(value),
    });
    chooseFile(icsFile());
    http.expectOne('/api/calendar').flush({ free_slots: SLOTS });
    chooseFile(icsFile());
    http
      .expectOne('/api/calendar')
      .flush({ error: 'Invalid .ics file', detail: null }, { status: 400, statusText: 'Bad Request' });
    chooseFile(icsFile(MAX_ICS_BYTES + 1));
    await fixture.whenStable();
    expect(cleared).toEqual(['', '', '']);
  });

  it('a failed upload keeps the plan on screen', async () => {
    await answerLoad(PLAN);
    chooseFile(icsFile());
    http
      .expectOne('/api/calendar')
      .flush({ error: 'Invalid .ics file', detail: null }, { status: 400, statusText: 'Bad Request' });
    const shown = await text();
    expect(shown).toContain('Your week of Mon 23 Nov');
    expect(alerts()).toEqual(['Invalid .ics file']);
  });

  it('turns off "Make my plan" while a calendar uploads', async () => {
    await answerLoad(null);
    chooseFile(icsFile());
    await fixture.whenStable();
    expect(makeButton().disabled).toBe(true);
    expect(fileInput().disabled).toBe(true);
    http.expectOne('/api/calendar').flush({ free_slots: SLOTS });
    await fixture.whenStable();
    expect(makeButton().disabled).toBe(false);
    expect(fileInput().disabled).toBe(false);
  });

  it('shows the error for an unreadable file', async () => {
    await answerLoad(null);
    chooseFile(icsFile());
    http
      .expectOne('/api/calendar')
      .flush({ error: 'Invalid .ics file', detail: null }, { status: 400, statusText: 'Bad Request' });
    expect(await text()).toContain('Invalid .ics file');
  });

  it('a new upload clears the plan on screen', async () => {
    await answerLoad(PLAN);
    chooseFile(icsFile());
    http.expectOne('/api/calendar').flush({ free_slots: SLOTS });
    const shown = await text();
    expect(shown).not.toContain('Your week of');
    expect(shown).toContain('No plan yet.');
  });

  it('a slow first load does not bring back the old plan after an upload', async () => {
    const load = http.expectOne('/api/plan/current');
    chooseFile(icsFile());
    http.expectOne('/api/calendar').flush({ free_slots: SLOTS });
    load.flush(PLAN);
    expect(await text()).not.toContain('Your week of');
    expect(status()).toBe('Found 3 free times on 2 days.');
  });

  it('stops showing "Loading your plan…" once the user acts', async () => {
    const load = http.expectOne('/api/plan/current');
    makeButton().click();
    http.expectOne('/api/plan').flush(PLAN);
    await fixture.whenStable();
    expect(status()).toBe('Your plan is ready.');
    load.flush(null, { status: 0, statusText: 'Unknown Error' });
    expect(await text()).not.toContain("Couldn't load your plan");
    expect(await text()).toContain('Your week of Mon 23 Nov');
  });

  it('makes a plan and shows it', async () => {
    await answerLoad(null);
    makeButton().click();
    expect(await text()).toContain('Making your plan…');
    expect(makeButton().disabled).toBe(true);
    expect(fileInput().disabled).toBe(true);
    const request = http.expectOne('/api/plan');
    expect(request.request.method).toBe('POST');
    request.flush(PLAN);
    const shown = await text();
    expect(shown).toContain('Your week of Mon 23 Nov');
    expect(shown).not.toContain('Making your plan…');
    expect(makeButton().disabled).toBe(false);
  });

  it('shows a refusal from the back end', async () => {
    await answerLoad(null);
    makeButton().click();
    refuse('/api/plan', 'Upload your calendar first, so the plan can fit your free time.');
    expect(await text()).toContain(
      'Request refused: Upload your calendar first, so the plan can fit your free time.',
    );
  });

  it('shows the problems when the plan fails its checks', async () => {
    await answerLoad(null);
    makeButton().click();
    http.expectOne('/api/plan').flush(
      {
        error: 'The plan did not pass the checks',
        detail: 'The plan has 2 sessions, but the profile asks for 3.',
      },
      { status: 502, statusText: 'Bad Gateway' },
    );
    expect(await text()).toContain(
      'The plan did not pass the checks: The plan has 2 sessions, but the profile asks for 3.',
    );
  });

  it('keeps the old plan on screen when a new plan fails', async () => {
    await answerLoad(PLAN);
    makeButton().click();
    refuse('/api/plan', 'Finish your profile first.');
    expect(await text()).toContain('Your week of Mon 23 Nov');
  });

  it('does not send a second plan request while one is pending', async () => {
    await answerLoad(null);
    makeButton().click();
    makeButton().click();
    http.expectOne('/api/plan').flush(PLAN);
    await fixture.whenStable();
  });
});
