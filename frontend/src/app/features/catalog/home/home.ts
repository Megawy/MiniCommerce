import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';

@Component({
  selector: 'mc-home',
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="hero">
      <h1>
        @if (auth.user(); as user) {
          Welcome back{{ user.first_name ? ', ' + user.first_name : '' }}.
        } @else {
          Gear for people who build things.
        }
      </h1>
      <p class="muted">Keyboards, mice, monitors and headsets — a demo storefront on a Django REST API.</p>
      <a routerLink="/products" class="btn btn--primary">Browse products</a>
    </section>
  `,
  styles: `
    .hero { padding: 2.5rem 0; max-width: 40rem; }
    .hero p { font-size: 1.1rem; }
  `,
})
export class Home {
  protected readonly auth = inject(AuthService);
}
