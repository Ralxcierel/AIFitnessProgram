import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LogEntry, PersonalBest } from '../core/api.types';
import { LogPage, today } from './log-page';

const SQUAT: LogEntry = {
  id: 1,
  date: '2026-11-20',
  exercise: 'Squat',
  sets: 3,
  reps: 5,
  weight_kg: 60,
};
const PUSH_UP: LogEntry = {
  id: 2,
  date: '2026-11-21',
  exercise: 'Push-up',
  sets: 3,
  reps: 15,
  weight_kg: null,
};
const BEST: PersonalBest = { exercise: 'Squat', best_weight_kg: 60, date: '2026-11-20' };

describe('today', () => {
  it('formats the date as YYYY-MM-DD in local time', () => {
    expect(today(new Date(2026, 0, 5, 23, 30))).toBe('2026-01-05');
  });
});

describe('LogPage', () => {
  let fixture: ComponentFixture<LogPage>;
  let http: HttpTestingController;

  const page = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const text = async (): Promise<string> => {
    await fixture.whenStable();
    return page().textContent ?? '';
  };
  const field = (id: string): HTMLInputElement =>
    page().querySelector(`#${id}`) as HTMLInputElement;
  const type = (id: string, value: string): void => {
    field(id).value = value;
    field(id).dispatchEvent(new Event('input'));
  };
  const submit = (): void => {
    (page().querySelector('form') as HTMLFormElement).dispatchEvent(new Event('submit'));
  };
  const answerLoad = async (entries: LogEntry[], bests: PersonalBest[]): Promise<void> => {
    http.expectOne({ method: 'GET', url: '/api/log' }).flush(entries);
    http.expectOne('/api/log/bests').flush(bests);
    await fixture.whenStable();
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [LogPage],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(LogPage);
  });

  afterEach(() => http.verify());

  it('starts with today in the date field', async () => {
    await answerLoad([], []);
    expect(field('date').value).toBe(today());
  });

  it('shows empty messages when nothing is logged', async () => {
    await answerLoad([], []);
    const shown = await text();
    expect(shown).toContain('Nothing logged yet.');
    expect(shown).toContain('No personal bests yet.');
  });

  it('shows the entries and the bests', async () => {
    await answerLoad([PUSH_UP, SQUAT], [BEST]);
    const cells = (selector: string): string[][] =>
      Array.from(page().querySelectorAll(`${selector} tbody tr`)).map((row) =>
        Array.from(row.querySelectorAll('td')).map((cell) => cell.textContent?.trim() ?? ''),
      );
    expect(cells('table.entries')).toEqual([
      ['2026-11-21', 'Push-up', '3', '15', '—'],
      ['2026-11-20', 'Squat', '3', '5', '60'],
    ]);
    expect(cells('table.bests')).toEqual([['Squat', '60', '2026-11-20']]);
  });

  it('says so when the log cannot be loaded', async () => {
    const bests = http.expectOne('/api/log/bests');
    http.expectOne('/api/log').error(new ProgressEvent('error'));
    expect(bests.cancelled).toBe(true);
    expect(await text()).toContain("Couldn't load your workout log.");
  });

  it('posts a new entry, then reloads the log and bests', async () => {
    await answerLoad([], []);
    type('date', '2026-11-22');
    type('exercise', '  Squat ');
    type('sets', '3');
    type('reps', '5');
    type('weight_kg', '62.5');
    submit();

    const request = http.expectOne({ method: 'POST', url: '/api/log' });
    expect(request.request.body).toEqual({
      id: null,
      date: '2026-11-22',
      exercise: 'Squat',
      sets: 3,
      reps: 5,
      weight_kg: 62.5,
    } satisfies LogEntry);
    const saved = { ...(request.request.body as LogEntry), id: 3 };
    request.flush(saved);
    await answerLoad([saved], [{ exercise: 'Squat', best_weight_kg: 62.5, date: '2026-11-22' }]);

    expect(await text()).toContain('Logged Squat.');
    expect(page().querySelector('table.bests')?.textContent).toContain('62.5');
    // Date and exercise stay for the next set; the numbers are cleared.
    expect(field('date').value).toBe('2026-11-22');
    expect(field('exercise').value).toBe('Squat');
    expect(field('sets').value).toBe('');
  });

  it('sends a null weight when the weight is left empty', async () => {
    await answerLoad([], []);
    type('exercise', 'Push-up');
    type('sets', '3');
    type('reps', '15');
    submit();
    const request = http.expectOne({ method: 'POST', url: '/api/log' });
    expect((request.request.body as LogEntry).weight_kg).toBeNull();
  });

  it('blocks bad values and does not post', async () => {
    await answerLoad([], []);
    type('exercise', '   ');
    type('sets', '0');
    type('reps', '2.5');
    type('weight_kg', '-1');
    submit();
    http.expectNone({ method: 'POST', url: '/api/log' });
    const shown = await text();
    expect(shown).toContain('Please fix the highlighted fields first.');
    expect(shown).toContain('Enter a name of up to 100 characters.');
    expect(shown).toContain('From 0 to 1000 kg, or leave it empty.');
    expect(field('sets').getAttribute('aria-invalid')).toBe('true');
    expect(field('reps').getAttribute('aria-invalid')).toBe('true');
  });

  it('blocks numbers above the upper limits', async () => {
    await answerLoad([], []);
    type('exercise', 'Squat');
    type('sets', '1001');
    type('reps', '1e20');
    type('weight_kg', '1000.5');
    submit();
    http.expectNone({ method: 'POST', url: '/api/log' });
    const shown = await text();
    expect(shown).toContain('A whole number from 1 to 1000.');
    expect(shown).toContain('From 0 to 1000 kg, or leave it empty.');
  });

  it('allows the upper limits themselves', async () => {
    await answerLoad([], []);
    type('exercise', 'Squat');
    type('sets', '1000');
    type('reps', '1000');
    type('weight_kg', '1000');
    submit();
    http.expectOne({ method: 'POST', url: '/api/log' });
  });

  it('links an error to its field only while the error is shown', async () => {
    await answerLoad([], []);
    expect(field('sets').getAttribute('aria-describedby')).toBeNull();
    type('sets', '0');
    submit();
    await fixture.whenStable();
    expect(field('sets').getAttribute('aria-describedby')).toBe('sets-error');
    expect(page().querySelector('#sets-error')).not.toBeNull();
    expect(field('date').getAttribute('aria-describedby')).toBeNull();
  });

  it('shows no empty-log messages while loading or after a load error', async () => {
    await fixture.whenStable();
    let shown = page().textContent ?? '';
    expect(shown).toContain('Loading your log…');
    expect(shown).not.toContain('Nothing logged yet.');
    http.expectOne('/api/log/bests');
    http.expectOne('/api/log').error(new ProgressEvent('error'));
    shown = await text();
    expect(shown).not.toContain('Nothing logged yet.');
    expect(shown).not.toContain('No personal bests yet.');
  });

  it('lets the newest reload win when reloads overlap', async () => {
    // The first load is still pending when an entry is added.
    await fixture.whenStable();
    const oldEntries = http.expectOne({ method: 'GET', url: '/api/log' });
    const oldBests = http.expectOne('/api/log/bests');
    type('exercise', 'Squat');
    type('sets', '3');
    type('reps', '5');
    submit();
    http.expectOne({ method: 'POST', url: '/api/log' }).flush({ ...SQUAT, id: 7 });
    expect(oldEntries.cancelled).toBe(true);
    expect(oldBests.cancelled).toBe(true);
    await answerLoad([{ ...SQUAT, id: 7 }], [BEST]);
    expect(page().querySelector('table.entries')?.textContent).toContain('Squat');
  });

  it('blocks an exercise name over 100 characters', async () => {
    await answerLoad([], []);
    expect(field('exercise').getAttribute('maxlength')).toBe('100');
    type('exercise', 'x'.repeat(101));
    type('sets', '1');
    type('reps', '1');
    submit();
    http.expectNone({ method: 'POST', url: '/api/log' });
  });

  it('shows the error the back end returns', async () => {
    await answerLoad([], []);
    type('exercise', 'Squat');
    type('sets', '3');
    type('reps', '5');
    submit();
    http
      .expectOne({ method: 'POST', url: '/api/log' })
      .flush(
        { error: 'Invalid request', detail: 'exercise: too long' },
        { status: 422, statusText: 'Unprocessable Entity' },
      );
    expect(await text()).toContain('Invalid request: exercise: too long');
  });
});
