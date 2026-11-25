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
});
