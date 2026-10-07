import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { Header } from '../header/header';

/** Application frame: header + main content (pages render in the outlet). */
@Component({
  selector: 'mc-shell',
  imports: [RouterOutlet, Header],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <a class="skip-link" href="#main">Skip to content</a>
    <mc-header />
    <main id="main" class="container main" tabindex="-1">
      <router-outlet />
    </main>
    <footer class="container footer">MiniCommerce · Angular + Django REST Framework</footer>
  `,
  styles: `
    :host { display: flex; flex-direction: column; min-height: 100dvh; }
    .main { flex: 1; padding-block: 2rem 3rem; outline: none; }
    .footer { padding-block: 1.5rem; color: var(--text-muted); font-size: .85rem; border-top: 1px solid var(--border); }
  `,
})
export class Shell {}
