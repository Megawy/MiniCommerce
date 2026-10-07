import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/** Inline message box. Errors use role="alert" so they are read out immediately. */
@Component({
  selector: 'mc-alert',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { '[attr.role]': "kind() === 'error' ? 'alert' : 'status'", '[class]': "'alert alert--' + kind()" },
  template: `<ng-content />`,
  styles: `
    :host { display: block; padding: .75rem 1rem; border-radius: var(--radius); border: 1px solid; font-size: .95rem; }
    :host(.alert--error) { color: var(--danger); background: var(--danger-soft); border-color: var(--danger-border); }
    :host(.alert--info) { color: var(--text); background: var(--surface-2); border-color: var(--border); }
  `,
})
export class Alert {
  readonly kind = input<'error' | 'info'>('info');
}
