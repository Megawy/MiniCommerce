import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { OrderStatus } from '../../shared/models/order';

const BADGES: Record<OrderStatus, string> = {
  PENDING: 'badge--warning',
  PAID: 'badge--success',
  COMPLETED: 'badge--success',
  CANCELLED: 'badge--danger',
};

@Component({
  selector: 'mc-order-status',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<span [class]="badge()">{{ label() }}</span>`,
})
export class OrderStatusBadge {
  readonly status = input.required<OrderStatus>();
  protected readonly badge = computed(() => 'badge ' + BADGES[this.status()]);
  protected readonly label = computed(() => this.status().charAt(0) + this.status().slice(1).toLowerCase());
}
