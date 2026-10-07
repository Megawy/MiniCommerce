import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AuthService } from '../../core/auth/auth.service';
import { Cart } from '../../shared/models/cart';
import { API, configureApiTest } from '../../testing';
import { CartService } from './cart.service';

const line = (id: number, quantity: number) => ({
  id,
  product: { id: id * 10, name: `P${id}`, slug: `p${id}`, price: '10.00' },
  quantity,
  subtotal: (10 * quantity).toFixed(2),
});
const cartOf = (...items: ReturnType<typeof line>[]): Cart => ({
  id: 1,
  items,
  total: items.reduce((t, i) => t + Number(i.subtotal), 0).toFixed(2),
});

function setup() {
  const http = configureApiTest({ authenticated: true });
  const service = TestBed.inject(CartService);
  TestBed.tick(); // run the "signed in -> load cart" effect
  http.expectOne(`${API}/cart/`).flush(cartOf(line(1, 2)));
  return { http, service };
}

describe('CartService', () => {
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('loads the cart when signed in and exposes the item count for the badge', () => {
    const { service } = setup();
    expect(service.cart()?.total).toBe('20.00');
    expect(service.itemCount()).toBe(2);
  });

  it('add posts product_id + quantity, then re-reads the cart', () => {
    const { http, service } = setup();
    service.add(20, 3).subscribe();
    const post = http.expectOne(`${API}/cart/items/`);
    expect(post.request.method).toBe('POST');
    expect(post.request.body).toEqual({ product_id: 20, quantity: 3 });
    post.flush(line(2, 3), { status: 201, statusText: 'Created' });
    http.expectOne(`${API}/cart/`).flush(cartOf(line(1, 2), line(2, 3)));
    expect(service.itemCount()).toBe(5);
  });

  it('updateQuantity patches the line, then re-reads the cart', () => {
    const { http, service } = setup();
    service.updateQuantity(1, 4).subscribe();
    const patch = http.expectOne(`${API}/cart/items/1/`);
    expect(patch.request.method).toBe('PATCH');
    expect(patch.request.body).toEqual({ quantity: 4 });
    patch.flush(line(1, 4));
    http.expectOne(`${API}/cart/`).flush(cartOf(line(1, 4)));
    expect(service.cart()?.total).toBe('40.00'); // the server's total, not one computed here
  });

  it('remove deletes the line, then re-reads the cart', () => {
    const { http, service } = setup();
    service.remove(1).subscribe();
    const del = http.expectOne(`${API}/cart/items/1/`);
    expect(del.request.method).toBe('DELETE');
    del.flush(null, { status: 204, statusText: 'No Content' });
    http.expectOne(`${API}/cart/`).flush(cartOf());
    expect(service.itemCount()).toBe(0);
  });

  it('clear deletes the whole cart, then re-reads it', () => {
    const { http, service } = setup();
    service.clear().subscribe();
    const del = http.expectOne(`${API}/cart/`);
    expect(del.request.method).toBe('DELETE');
    del.flush(null, { status: 204, statusText: 'No Content' });
    http.expectOne(`${API}/cart/`).flush(cartOf());
    expect(service.cart()?.items).toEqual([]);
  });

  it('a failed add leaves the cart untouched and surfaces the error', () => {
    const { http, service } = setup();
    let error: unknown;
    service.add(20, 99).subscribe({ error: (e) => (error = e) });
    http.expectOne(`${API}/cart/items/`).flush({ quantity: ['Only 3 left in stock.'] }, { status: 400, statusText: 'Bad Request' });
    expect(error).toBeTruthy();
    expect(service.itemCount()).toBe(2);
  });

  it('forgets the cart on logout', () => {
    const { service } = setup();
    TestBed.inject(AuthService).logout();
    TestBed.tick();
    expect(service.cart()).toBeNull();
    expect(service.itemCount()).toBe(0);
  });
});
