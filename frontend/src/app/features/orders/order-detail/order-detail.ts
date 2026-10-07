import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, booleanAttribute, computed, inject, input } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

import { apiErrorMessage } from '../../../core/http/api-error';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { Alert } from '../../../shared/ui/alert';
import { Spinner } from '../../../shared/ui/spinner';
import { OrderStatusBadge } from '../order-status';
import { OrderService } from '../order.service';

@Component({
  selector: 'mc-order-detail',
  imports: [DatePipe, RouterLink, MoneyPipe, Alert, Spinner, OrderStatusBadge],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <a routerLink="/orders" class="back">← All orders</a>

    @if (order.isLoading()) {
      <mc-spinner label="Loading order…" />
    } @else if (notFound()) {
      <!-- Another user's order is a 404 too: the API never confirms it exists. -->
      <div class="empty">
        <h1>Order not found</h1>
        <a routerLink="/orders" class="btn btn--primary">Back to your orders</a>
      </div>
    } @else if (errorMessage(); as message) {
      <mc-alert kind="error">
        {{ message }}
        <button type="button" class="btn btn--ghost" (click)="order.reload()">Retry</button>
      </mc-alert>
    } @else if (order.value(); as o) {
      @if (placed()) {
        <mc-alert kind="info" class="placed" data-testid="order-placed">
          Thank you! Order #{{ o.id }} was placed. A confirmation email is on its way.
        </mc-alert>
      }
      <header class="page-header order__header">
        <h1>Order #{{ o.id }}</h1>
        <mc-order-status [status]="o.status" />
      </header>
      <p class="muted">Placed {{ o.created_at | date: 'medium' }}</p>

      <table class="table">
        <caption class="visually-hidden">Items in order {{ o.id }}</caption>
        <thead>
          <tr>
            <th scope="col">Product</th>
            <th scope="col" class="num">Unit price</th>
            <th scope="col" class="num">Qty</th>
            <th scope="col" class="num">Subtotal</th>
          </tr>
        </thead>
        <tbody>
          @for (item of o.items; track item.id) {
            <tr data-testid="order-item">
              <td><a [routerLink]="['/products', item.product.id]">{{ item.product.name }}</a></td>
              <!-- Price paid at checkout (OrderItem.price snapshot), not today's product price. -->
              <td class="num">{{ item.price | money }}</td>
              <td class="num">{{ item.quantity }}</td>
              <td class="num price">{{ item.subtotal | money }}</td>
            </tr>
          }
        </tbody>
        <tfoot>
          <tr><th scope="row" colspan="3" class="num">Total</th><td class="num price" data-testid="order-total">{{ o.total | money }}</td></tr>
        </tfoot>
      </table>
      <p class="muted note">Prices shown are what you paid at checkout.</p>
    }
  `,
  styles: `
    .back { display: inline-block; margin-bottom: 1rem; text-decoration: none; }
    .placed { margin-bottom: 1rem; }
    .order__header { display: flex; align-items: center; gap: 1rem; margin-bottom: .25rem; }
    .order__header h1 { margin: 0; }
    tfoot th, tfoot td { border-top: 1px solid var(--border); font-size: 1.05rem; }
    .note { margin-top: .75rem; font-size: .85rem; }
  `,
})
export class OrderDetail {
  private readonly service = inject(OrderService);

  readonly id = input.required<string>();
  /** ?placed=1 after checkout. */
  readonly placed = input(false, { transform: booleanAttribute });

  protected readonly order = rxResource({
    params: () => this.id(),
    stream: ({ params }) => this.service.get(params),
  });
  protected readonly notFound = computed(() => {
    const err = this.order.error();
    return err instanceof HttpErrorResponse && err.status === 404;
  });
  protected readonly errorMessage = computed(() => (this.order.error() ? apiErrorMessage(this.order.error()) : null));
}
