import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';

import { API, configureApiTest, text } from '../../../testing';
import { ProductDetail } from './product-detail';

const MOUSE = {
  id: 5, name: 'Mouse', slug: 'mouse', description: 'Fast', price: '49.00', stock: 3, is_active: true,
  category: { id: 2, name: 'Mice', slug: 'mice' }, created_at: '', updated_at: '',
};

async function setup(authenticated: boolean) {
  const http = configureApiTest({ authenticated });
  const fixture = TestBed.createComponent(ProductDetail);
  fixture.componentRef.setInput('id', '5');
  fixture.detectChanges();
  TestBed.tick();
  if (authenticated) http.expectOne(`${API}/cart/`).flush({ id: 1, items: [], total: '0.00' });
  http.expectOne(`${API}/products/5/`).flush(MOUSE);
  await fixture.whenStable();
  const el = fixture.nativeElement as HTMLElement;
  const add = () => el.querySelector<HTMLButtonElement>('[data-testid="add-to-cart"]')!.click();
  return { http, fixture, el, add, router: TestBed.inject(Router) };
}

describe('ProductDetail', () => {
  it('sends anonymous shoppers to login with a returnUrl instead of calling the API', async () => {
    const { add, router } = await setup(false);
    vi.spyOn(router, 'url', 'get').mockReturnValue('/products/5');
    const navigate = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    add();
    expect(navigate).toHaveBeenCalledWith(['/login'], { queryParams: { returnUrl: '/products/5' } });
  });

  it('adds to the cart, refreshes the badge and confirms', async () => {
    const { http, fixture, el, add } = await setup(true);
    add();
    await fixture.whenStable();
    expect(el.querySelector<HTMLButtonElement>('[data-testid="add-to-cart"]')!.disabled).toBe(true); // in flight
    const post = http.expectOne(`${API}/cart/items/`);
    expect(post.request.body).toEqual({ product_id: 5, quantity: 1 });
    post.flush({}, { status: 201, statusText: 'Created' });
    http.expectOne(`${API}/cart/`).flush({ id: 1, items: [], total: '49.00' });
    await fixture.whenStable();
    expect(text(el.querySelector('mc-alert')!)).toContain('Added to your cart.');
  });

  it("shows the API's stock message when the add is rejected", async () => {
    const { http, fixture, el, add } = await setup(true);
    add();
    http.expectOne(`${API}/cart/items/`).flush({ quantity: ['Only 3 left in stock.'] }, { status: 400, statusText: 'Bad Request' });
    await fixture.whenStable();
    expect(text(el.querySelector('mc-alert')!)).toBe('Only 3 left in stock.');
  });

  it('shows "Product not found" for a 404', async () => {
    const http = configureApiTest();
    const fixture = TestBed.createComponent(ProductDetail);
    fixture.componentRef.setInput('id', '999');
    fixture.detectChanges();
    TestBed.tick();
    http.expectOne(`${API}/products/999/`).flush({ detail: 'No Product matches the given query.' }, { status: 404, statusText: 'Not Found' });
    await fixture.whenStable();
    expect(text(fixture.nativeElement)).toContain('Product not found');
  });
});
