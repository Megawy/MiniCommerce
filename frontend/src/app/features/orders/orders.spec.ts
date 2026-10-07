import { Type } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { API, configureApiTest, text } from '../../testing';
import { OrderDetail } from './order-detail/order-detail';
import { OrderList } from './order-list/order-list';

function create<T>(component: Type<T>, inputs: Record<string, unknown>) {
  const http = configureApiTest({ authenticated: true });
  const fixture = TestBed.createComponent(component);
  for (const [k, v] of Object.entries(inputs)) fixture.componentRef.setInput(k, v);
  fixture.detectChanges();
  TestBed.tick();
  http.match(`${API}/cart/`); // badge refresh, not under test
  return { http, fixture, el: fixture.nativeElement as HTMLElement };
}

describe('Orders', () => {
  it('lists orders with status and total', async () => {
    const { http, fixture, el } = create(OrderList, { page: '1' });
    http.expectOne(`${API}/orders/?page=1`).flush({
      count: 2, next: null, previous: null,
      results: [
        { id: 2, status: 'PAID', total: '59.00', created_at: '2026-10-07T10:00:00Z', updated_at: '' },
        { id: 1, status: 'CANCELLED', total: '10.00', created_at: '2026-10-01T10:00:00Z', updated_at: '' },
      ],
    });
    await fixture.whenStable();
    const rows = el.querySelectorAll('[data-testid="order-row"]');
    expect(rows.length).toBe(2);
    expect(text(rows[0])).toContain('#2');
    expect(text(rows[0])).toContain('Paid');
    expect(text(rows[0])).toContain('$59.00');
  });

  it('shows order items at the historical (checkout) price', async () => {
    const { http, fixture, el } = create(OrderDetail, { id: '2', placed: '1' });
    http.expectOne(`${API}/orders/2/`).flush({
      id: 2, status: 'PAID', total: '118.00', created_at: '2026-10-07T10:00:00Z', updated_at: '',
      items: [{ id: 9, product: { id: 5, name: 'Mouse', slug: 'mouse' }, quantity: 2, price: '59.00', subtotal: '118.00' }],
    });
    await fixture.whenStable();
    const cells = [...el.querySelectorAll('[data-testid="order-item"] td')].map(text);
    expect(cells).toEqual(['Mouse', '$59.00', '2', '$118.00']);
    expect(text(el.querySelector('[data-testid="order-total"]')!)).toBe('$118.00');
    expect(el.querySelector('[data-testid="order-placed"]')).not.toBeNull();
  });

  it("another user's order (404) shows 'Order not found'", async () => {
    const { http, fixture, el } = create(OrderDetail, { id: '77' });
    http.expectOne(`${API}/orders/77/`).flush({ detail: 'No Order matches the given query.' }, { status: 404, statusText: 'Not Found' });
    await fixture.whenStable();
    expect(text(el)).toContain('Order not found');
  });
});
