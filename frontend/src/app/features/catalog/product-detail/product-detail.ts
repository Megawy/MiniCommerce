import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { apiErrorMessage } from '../../../core/http/api-error';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { Alert } from '../../../shared/ui/alert';
import { Spinner } from '../../../shared/ui/spinner';
import { CartService } from '../../cart/cart.service';
import { ProductService } from '../product.service';

@Component({
  selector: 'mc-product-detail',
  imports: [RouterLink, MoneyPipe, Alert, Spinner],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './product-detail.html',
  styleUrl: './product-detail.css',
})
export class ProductDetail {
  private readonly products = inject(ProductService);
  private readonly cart = inject(CartService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  /** Route param :id (withComponentInputBinding). */
  readonly id = input.required<string>();

  protected readonly product = rxResource({
    params: () => this.id(),
    stream: ({ params }) => this.products.get(params),
  });

  protected readonly notFound = computed(() => {
    const err = this.product.error();
    return err instanceof HttpErrorResponse && err.status === 404;
  });
  protected readonly loadError = computed(() => (this.product.error() ? apiErrorMessage(this.product.error()) : null));

  protected readonly quantity = signal(1);
  protected readonly adding = signal(false);
  protected readonly added = signal(false);
  protected readonly addError = signal<string | null>(null);

  protected setQuantity(value: string | number): void {
    const n = Math.floor(Number(value));
    this.quantity.set(Number.isFinite(n) && n > 0 ? n : 1);
  }

  protected addToCart(): void {
    const product = this.product.value();
    if (!product || this.adding()) return;
    // Anonymous: sign in first, then come back to this product.
    if (!this.auth.isAuthenticated()) {
      void this.router.navigate(['/login'], { queryParams: { returnUrl: this.router.url } });
      return;
    }
    this.adding.set(true);
    this.added.set(false);
    this.addError.set(null);
    // Stock and "is it still active?" are checked by Django; we show its message (400) as-is.
    this.cart.add(product.id, this.quantity()).subscribe({
      next: () => {
        this.added.set(true);
        this.adding.set(false);
      },
      error: (err) => {
        this.addError.set(apiErrorMessage(err));
        this.adding.set(false);
      },
    });
  }
}
