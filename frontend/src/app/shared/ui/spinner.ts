import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/** Loading indicator. Announced to screen readers via role="status". */
@Component({
  selector: 'mc-spinner',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="spinner" role="status">
      <span class="spinner__ring" aria-hidden="true"></span>
      <span>{{ label() }}</span>
    </div>
  `,
  styles: `
    .spinner { display: inline-flex; align-items: center; gap: .6rem; color: var(--text-muted); }
    .spinner__ring {
      width: 1.1rem; height: 1.1rem; border-radius: 50%;
      border: 2px solid var(--border); border-top-color: var(--accent);
      animation: spin .8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    @media (prefers-reduced-motion: reduce) { .spinner__ring { animation-duration: 2.4s; } }
  `,
})
export class Spinner {
  readonly label = input('Loading…');
}
