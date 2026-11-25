import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ApiService } from './api.service';
import { HealthResponse } from './api.types';

describe('ApiService', () => {
  it('gets the health status', () => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const http = TestBed.inject(HttpTestingController);
    let result: HealthResponse | undefined;

    TestBed.inject(ApiService)
      .getHealth()
      .subscribe((health) => (result = health));
    const request = http.expectOne('/api/health');
    request.flush({ status: 'ok' });

    expect(request.request.method).toBe('GET');
    expect(result).toEqual({ status: 'ok' });
    http.verify();
  });
});
