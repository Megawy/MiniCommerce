import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { API_BASE_URL } from '../../core/http/api.config';
import { Paginated } from '../../shared/models/api';
import { Order, OrderSummary } from '../../shared/models/order';

@Injectable({ providedIn: 'root' })
export class OrderService {
  private readonly http = inject(HttpClient);
  private readonly api = inject(API_BASE_URL);

  list(page = 1): Observable<Paginated<OrderSummary>> {
    return this.http.get<Paginated<OrderSummary>>(`${this.api}/orders/`, { params: { page } });
  }

  get(id: number | string): Observable<Order> {
    return this.http.get<Order>(`${this.api}/orders/${id}/`);
  }

  /**
   * Turn the cart into a PAID order. No body: Django reads the cart, locks stock, snapshots prices,
   * charges the (mock) payment and clears the cart in one transaction.
   */
  checkout(): Observable<Order> {
    return this.http.post<Order>(`${this.api}/orders/checkout/`, null);
  }
}
