import { ChangeDetectionStrategy, Component, computed, inject, input, numberAttribute } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { Router, RouterLink } from '@angular/router';

import { apiErrorMessage } from '../../../core/http/api-error';
import { ProductQuery } from '../../../shared/models/catalog';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { Alert } from '../../../shared/ui/alert';
import { Pager } from '../../../shared/ui/pager';
import { Spinner } from '../../../shared/ui/spinner';
import { CategoryService } from '../category.service';
import { ProductService } from '../product.service';

export const PRODUCT_PAGE_SIZE = 12;

const ORDERINGS: { value: NonNullable<ProductQuery['ordering']>; label: string }[] = [
  { value: '-created_at', label: 'Newest' },
  { value: 'name', label: 'Name (A–Z)' },
  { value: 'price', label: 'Price: low to high' },
  { value: '-price', label: 'Price: high to low' },
];

/**
 * The URL is the state: ?search=&category=&ordering=&page= are bound to inputs
 * (withComponentInputBinding), so filters survive refresh, back/forward and sharing a link.
 * Controls only navigate; the resource re-fetches when the inputs change.
 */
@Component({
  selector: 'mc-product-list',
  imports: [RouterLink, MoneyPipe, Alert, Pager, Spinner],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './product-list.html',
  styleUrl: './product-list.css',
})
export class ProductList {
  private readonly router = inject(Router);
  private readonly products = inject(ProductService);
  private readonly categoryService = inject(CategoryService);

  readonly search = input<string>();
  readonly category = input<string>();
  readonly ordering = input<string>();
  readonly page = input(1, { transform: (v: unknown) => numberAttribute(v, 1) || 1 });

  protected readonly orderings = ORDERINGS;
  protected readonly pageSize = PRODUCT_PAGE_SIZE;

  protected readonly query = computed<ProductQuery>(() => ({
    search: this.search()?.trim() || undefined,
    category: this.category() || undefined,
    ordering: ORDERINGS.some((o) => o.value === this.ordering())
      ? (this.ordering() as ProductQuery['ordering'])
      : undefined,
    page: this.page(),
    page_size: PRODUCT_PAGE_SIZE,
  }));

  protected readonly result = rxResource({
    params: () => this.query(),
    stream: ({ params }) => this.products.list(params),
  });

  protected readonly categories = rxResource({ stream: () => this.categoryService.list() });

  protected readonly errorMessage = computed(() =>
    this.result.error() ? apiErrorMessage(this.result.error()) : null,
  );
  protected readonly filtered = computed(() => !!(this.search() || this.category()));

  /** Change filters -> new URL (page resets unless it is the page itself that changes). */
  protected setQuery(changes: Partial<Record<'search' | 'category' | 'ordering' | 'page', string | number | null>>): void {
    void this.router.navigate([], {
      queryParams: { page: null, ...changes },
      queryParamsHandling: 'merge',
    });
  }

  protected onSearch(event: Event, value: string): void {
    event.preventDefault();
    this.setQuery({ search: value.trim() || null });
  }

  protected clearFilters(): void {
    void this.router.navigate([], { queryParams: {} });
  }
}
