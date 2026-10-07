import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, input, numberAttribute } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { Router, RouterLink } from '@angular/router';

import { apiErrorMessage } from '../../../core/http/api-error';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { Alert } from '../../../shared/ui/alert';
import { Pager } from '../../../shared/ui/pager';
import { Spinner } from '../../../shared/ui/spinner';
import { OrderStatusBadge } from '../order-status';
import { OrderService } from '../order.service';

/** DRF default PAGE_SIZE for /api/orders/. */
const ORDER_PAGE_SIZE = 20;

@Component({
  selector: 'mc-order-list',
  imports: [DatePipe, RouterLink, MoneyPipe, Alert, Pager, Spinner, OrderStatusBadge],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="page-header"><h1>Your orders</h1></header>

    @if (errorMessage(); as message) {
      <mc-alert kind="error">
        {{ message }}
        <button type="button" class="btn btn--ghost" (click)="orders.reload()">Retry</button>
      </mc-alert>
    } @else if (orders.isLoading() && !orders.hasValue()) {
      <mc-spinner label="Loading orders…" />
    } @else if (orders.value(); as data) {
      @if (data.results.length === 0) {
        <div class="empty">
          <h2>No orders yet</h2>
          <p>Orders you place will appear here.</p>
          <a routerLink="/products" class="btn btn--primary">Start shopping</a>
        </div>
      } @else {
        <table class="table">
          <caption class="visually-hidden">Your orders, newest first</caption>
          <thead>
            <tr><th scope="col">Order</th><th scope="col">Placed</th><th scope="col">Status</th><th scope="col" class="num">Total</th></tr>
          </thead>
          <tbody>
            @for (o of data.results; track o.id) {
              <tr data-testid="order-row">
                <td><a [routerLink]="['/orders', o.id]">#{{ o.id }}</a></td>
                <td>{{ o.created_at | date: 'medium' }}</td>
                <td><mc-order-status [status]="o.status" /></td>
                <td class="num price">{{ o.total | money }}</td>
              </tr>
            }
          </tbody>
        </table>
        <mc-pager [page]="page()" [count]="data.count" [pageSize]="pageSize" (pageChange)="goTo($event)" />
      }
    }
  `,
})
export class OrderList {
  private readonly service = inject(OrderService);
  private readonly router = inject(Router);

  readonly page = input(1, { transform: (v: unknown) => numberAttribute(v, 1) || 1 });
  protected readonly pageSize = ORDER_PAGE_SIZE;

  protected readonly orders = rxResource({
    params: () => this.page(),
    stream: ({ params }) => this.service.list(params),
  });
  protected readonly errorMessage = computed(() => (this.orders.error() ? apiErrorMessage(this.orders.error()) : null));

  protected goTo(page: number): void {
    void this.router.navigate([], { queryParams: { page } });
  }
}
