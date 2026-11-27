import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { App } from './app';
import { routes } from './app.routes';

describe('App', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter(routes), provideHttpClient(), provideHttpClientTesting()],
    });
  });

  for (const path of ['/', '/no-such-page']) {
    it(`shows the home page at ${path}`, async () => {
      const fixture = TestBed.createComponent(App);
      fixture.detectChanges();
      await TestBed.inject(Router).navigateByUrl(path);
      TestBed.inject(HttpTestingController).expectOne('/api/health').flush({ status: 'ok' });
      await fixture.whenStable();

      const page = fixture.nativeElement as HTMLElement;
      expect(page.querySelector('main h1')?.textContent).toBe('Fitness Planner');
    });
  }

  it('shows the profile page at /profile, with links to every page', async () => {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    await TestBed.inject(Router).navigateByUrl('/profile');
    TestBed.inject(HttpTestingController).expectOne('/api/profile').flush({
      name: null,
      height_cm: null,
      weight_kg: null,
      experience: null,
      goals: [],
      workout_days: null,
      session_minutes: null,
      split_preference: null,
      equipment: [],
      injuries: [],
      health_notes: null,
      dietary_preferences: [],
      dietary_restrictions: [],
    });
    await fixture.whenStable();

    const page = fixture.nativeElement as HTMLElement;
    expect(page.querySelector('main h1')?.textContent).toBe('Your profile');
    const links = Array.from(page.querySelectorAll('nav a')).map((a) => a.getAttribute('href'));
    expect(links).toEqual(['/', '/profile', '/plan', '/log']);
  });

  it('shows the plan page at /plan', async () => {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    await TestBed.inject(Router).navigateByUrl('/plan');
    TestBed.inject(HttpTestingController)
      .expectOne('/api/plan/current')
      .flush({ error: 'No plan yet', detail: null }, { status: 404, statusText: 'Not Found' });
    await fixture.whenStable();

    const page = fixture.nativeElement as HTMLElement;
    expect(page.querySelector('main h1')?.textContent).toBe('Weekly plan');
  });

  it('shows the workout log page at /log', async () => {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    await TestBed.inject(Router).navigateByUrl('/log');
    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/log').flush([]);
    http.expectOne('/api/log/bests').flush([]);
    await fixture.whenStable();

    const page = fixture.nativeElement as HTMLElement;
    expect(page.querySelector('main h1')?.textContent).toBe('Workout log');
  });
});
