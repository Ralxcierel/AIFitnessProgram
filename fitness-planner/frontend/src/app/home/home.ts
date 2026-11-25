import { Component, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ApiService } from '../core/api.service';

/** Landing page: shows whether the back end is reachable. */
@Component({
  selector: 'app-home',
  templateUrl: './home.html',
})
export class Home {
  protected readonly status = signal('checking…');
  protected readonly failed = signal(false);

  constructor() {
    inject(ApiService)
      .getHealth()
      .pipe(takeUntilDestroyed())
      .subscribe({
        next: (health) => this.status.set(health.status),
        error: () => this.failed.set(true),
      });
  }
}
