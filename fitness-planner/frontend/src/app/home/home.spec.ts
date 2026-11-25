import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Home } from './home';

describe('Home', () => {
  let fixture: ComponentFixture<Home>;
  let http: HttpTestingController;

  const text = async (): Promise<string> => {
    await fixture.whenStable();
    return (fixture.nativeElement as HTMLElement).textContent ?? '';
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [Home],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Home);
  });

  afterEach(() => http.verify());

  it('shows that it is checking, then the status', async () => {
    const request = http.expectOne('/api/health');
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('checking…');
    request.flush({ status: 'ok' });
    expect(await text()).toContain('Back end status: ok');
  });

  it('says so when the back end answers with an error', async () => {
    http.expectOne('/api/health').flush('', { status: 500, statusText: 'Server Error' });
    expect(await text()).toContain("Can't connect");
    expect(await text()).not.toContain('Back end status');
  });

  it('says so when the back end cannot be reached', async () => {
    http.expectOne('/api/health').error(new ProgressEvent('error'));
    expect(await text()).toContain("Can't connect");
  });
});
