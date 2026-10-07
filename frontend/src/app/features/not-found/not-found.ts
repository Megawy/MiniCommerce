import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'mc-not-found',
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <h1>Page not found</h1>
    <p class="muted">That page doesn't exist.</p>
    <a routerLink="/" class="btn btn--secondary">Go home</a>
  `,
})
export class NotFound {}
