import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';

import { API, configureApiTest, text } from '../../testing';
import { CartPage } from './cart-page';

const CART = {
  id: 1,
  items: [{ id: 3, product: { id: 7, name: 'Keyboard', slug: 'kb', price: '100.00' }, quantity: 2, subtotal: '200.00' }],
  total: '200.00',
};
const EMPTY = { id: 1, items: [], total: '0.00' };

async function setup() {
  const http = configureApiTest({ authenticated: true });
  const fixture = TestBed.createComponent(CartPage);
  fixture.detectChanges();
  TestBed.tick();
  // CartService's session effect and the page both read the cart.
  for (const req of http.match(`${API}/cart/`)) req.flush(CART);
  await fixture.whenStable();
  const el = fixture.nativeElement as HTMLElement;
  const button = (sel: string) => el.querySelector<HTMLButtonElement>(sel)!;
  return { http, fixture, el, button, router: TestBed.inject(Router) };
}

describe('CartPage', () => {
  it('renders lines and the server total', async () => {
    const { el } = await setup();
    expect(el.querySelectorAll('[data-testid="cart-line"]').length).toBe(1);
    expect(text(el.querySelector('[data-testid="cart-total"]')!)).toBe('$200.00');
  });

  it('increments quantity through the API', async () => {
    const { http, fixture, el } = await setup();
    el.querySelector<HTMLButtonElement>('[aria-label="Increase quantity of Keyboard"]')!.click();
    const patch = http.expectOne(`${API}/cart/items/3/`);
    expect(patch.request.body).toEqual({ quantity: 3 });
    patch.flush({});
    http.expectOne(`${API}/cart/`).flush({ ...CART, items: [{ ...CART.items[0], quantity: 3, subtotal: '300.00' }], total: '300.00' });
    await fixture.whenStable();
    expect(text(el.querySelector('[data-testid="quantity"]')!)).toBe('3');
  });

  it('checkout: disables the button, submits once, refreshes the cart and opens the order', async () => {
    const { http, fixture, button, router } = await setup();
    const navigate = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    button('[data-testid="checkout"]').click();
    await fixture.whenStable();
    expect(button('[data-testid="checkout"]').disabled).toBe(true);
    expect(button('[data-testid="checkout"]').textContent).toContain('Placing order');
    button('[data-testid="checkout"]').click(); // double click: ignored

    const post = http.expectOne(`${API}/orders/checkout/`); // exactly one
    expect(post.request.method).toBe('POST');
    post.flush({ id: 42, status: 'PAID', total: '200.00', items: [], created_at: '', updated_at: '' }, { status: 201, statusText: 'Created' });
    http.expectOne(`${API}/cart/`).flush(EMPTY);
    await fixture.whenStable();

    expect(navigate).toHaveBeenCalledWith(['/orders', 42], { queryParams: { placed: 1 } });
  });

  it("checkout failure shows the API's message and re-reads the cart", async () => {
    const { http, fixture, el, button } = await setup();
    button('[data-testid="checkout"]').click();
    http
      .expectOne(`${API}/orders/checkout/`)
      .flush({ detail: 'Not enough stock for Keyboard: 1 available.' }, { status: 400, statusText: 'Bad Request' });
    http.expectOne(`${API}/cart/`).flush(CART);
    await fixture.whenStable();

    expect(text(el.querySelector('mc-alert')!)).toBe('Not enough stock for Keyboard: 1 available.');
    expect(button('[data-testid="checkout"]').disabled).toBe(false);
  });
});
