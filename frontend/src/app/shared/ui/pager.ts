import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';

/** Previous / "Page x of y" / Next for DRF PageNumberPagination. */
@Component({
  selector: 'mc-pager',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (pages() > 1) {
      <nav class="pager" aria-label="Pagination">
        <button type="button" class="btn btn--secondary" [disabled]="page() <= 1" (click)="pageChange.emit(page() - 1)">
          Previous
        </button>
        <span class="muted" aria-live="polite">Page {{ page() }} of {{ pages() }}</span>
        <button type="button" class="btn btn--secondary" [disabled]="page() >= pages()" (click)="pageChange.emit(page() + 1)">
          Next
        </button>
      </nav>
    }
  `,
  styles: `.pager { display: flex; align-items: center; justify-content: center; gap: 1rem; margin-top: 2rem; }`,
})
export class Pager {
  readonly page = input.required<number>();
  readonly count = input.required<number>();
  readonly pageSize = input.required<number>();
  readonly pageChange = output<number>();

  protected readonly pages = computed(() => Math.max(1, Math.ceil(this.count() / this.pageSize())));
}
