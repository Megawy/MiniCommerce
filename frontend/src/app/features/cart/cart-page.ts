import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { Observable, catchError, finalize, map, of, switchMap } from 'rxjs';

import { apiErrorMessage } from '../../core/http/api-error';
import { CartItem } from '../../shared/models/cart';
import { MoneyPipe } from '../../shared/pipes/money.pipe';
import { Alert } from '../../shared/ui/alert';
import { Spinner } from '../../shared/ui/spinner';
import { OrderService } from '../orders/order.service';
import { CartService } from './cart.service';

@Component({
  selector: 'mc-cart-page',
  imports: [RouterLink, MoneyPipe, Alert, Spinner],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './cart-page.html',
  styleUrl: './cart-page.css',
})
export class CartPage {
  protected readonly cartService = inject(CartService);
  private readonly orders = inject(OrderService);
  private readonly router = inject(Router);

  protected readonly cart = this.cartService.cart;
  protected readonly loading = signal(true);
  protected readonly loadError = signal<string | null>(null);
  /** One mutation at a time: buttons are disabled while anything is in flight. */
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly checkingOut = signal(false);
  protected readonly confirmingClear = signal(false);

  constructor() {
    this.reload();
  }

  protected reload(): void {
    this.loading.set(true);
    this.loadError.set(null);
    this.cartService
      .load()
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({ error: (err) => this.loadError.set(apiErrorMessage(err)) });
  }

  protected changeQuantity(item: CartItem, delta: number): void {
    const quantity = item.quantity + delta;
    if (quantity < 1) return;
    this.run(this.cartService.updateQuantity(item.id, quantity));
  }

  protected remove(item: CartItem): void {
    this.run(this.cartService.remove(item.id));
  }

  protected clear(): void {
    this.confirmingClear.set(false);
    this.run(this.cartService.clear());
  }

  /**
   * POST /orders/checkout/ -> Django locks stock, snapshots prices, takes payment and empties the cart
   * atomically. The button is disabled while the request runs, so a double click can't submit twice.
   */
  protected checkout(): void {
    if (this.checkingOut() || this.busy()) return;
    this.checkingOut.set(true);
    this.error.set(null);
    this.orders
      .checkout()
      .pipe(
        // Server emptied the cart: re-read it so the header badge goes to 0, then show the order.
        // (A failed refresh must not hide a successful order.)
        switchMap((order) => this.cartService.load().pipe(catchError(() => of(null)), map(() => order))),
        switchMap((order) => this.router.navigate(['/orders', order.id], { queryParams: { placed: 1 } })),
        finalize(() => this.checkingOut.set(false)),
      )
      .subscribe({
        error: (err) => {
          this.error.set(apiErrorMessage(err));
          // Stock or prices may have moved under us: show the cart as it is now.
          this.cartService.load().subscribe({ error: () => undefined });
        },
      });
  }

  private run(action: Observable<unknown>): void {
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set(null);
    action.pipe(finalize(() => this.busy.set(false))).subscribe({
      error: (err) => {
        this.error.set(apiErrorMessage(err));
        this.cartService.load().subscribe({ error: () => undefined });
      },
    });
  }
}
