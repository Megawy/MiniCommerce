import { HttpClient } from '@angular/common/http';
import { Injectable, computed, effect, inject, signal, untracked } from '@angular/core';
import { Observable, switchMap, tap } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { API_BASE_URL } from '../../core/http/api.config';
import { Cart, CartItem } from '../../shared/models/cart';

/**
 * The signed-in user's cart. Django is authoritative for prices, stock, quantities and totals:
 * after every change the cart is re-read from the API instead of being recalculated here.
 * The `cart` signal feeds the header badge and the cart page.
 */
@Injectable({ providedIn: 'root' })
export class CartService {
  private readonly http = inject(HttpClient);
  private readonly api = inject(API_BASE_URL);
  private readonly auth = inject(AuthService);

  private readonly cartSignal = signal<Cart | null>(null);
  readonly cart = this.cartSignal.asReadonly();
  readonly itemCount = computed(() => this.cartSignal()?.items.reduce((n, item) => n + item.quantity, 0) ?? 0);

  constructor() {
    // Signed in -> fetch the cart for the badge; signed out -> forget it.
    effect(() => {
      const authenticated = this.auth.isAuthenticated();
      untracked(() => {
        if (authenticated) this.load().subscribe({ error: () => undefined });
        else this.cartSignal.set(null);
      });
    });
  }

  load(): Observable<Cart> {
    return this.http.get<Cart>(`${this.api}/cart/`).pipe(tap((cart) => this.cartSignal.set(cart)));
  }

  /** Add (or merge into an existing line — the API decides), then refresh. */
  add(productId: number, quantity: number): Observable<Cart> {
    return this.http
      .post<CartItem>(`${this.api}/cart/items/`, { product_id: productId, quantity })
      .pipe(switchMap(() => this.load()));
  }

  updateQuantity(itemId: number, quantity: number): Observable<Cart> {
    return this.http
      .patch<CartItem>(`${this.api}/cart/items/${itemId}/`, { quantity })
      .pipe(switchMap(() => this.load()));
  }

  remove(itemId: number): Observable<Cart> {
    return this.http.delete<void>(`${this.api}/cart/items/${itemId}/`).pipe(switchMap(() => this.load()));
  }

  clear(): Observable<Cart> {
    return this.http.delete<void>(`${this.api}/cart/`).pipe(switchMap(() => this.load()));
  }
}
