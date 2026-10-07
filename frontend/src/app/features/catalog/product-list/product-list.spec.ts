import { TestBed } from '@angular/core/testing';

import { API, configureApiTest, text } from '../../../testing';
import { ProductList } from './product-list';

const product = (id: number, stock = 10) => ({
  id, name: `Keyboard ${id}`, slug: `kb-${id}`, description: 'Clicky', price: '129.00', stock, is_active: true,
  category: { id: 1, name: 'Keyboards', slug: 'keyboards' }, created_at: '', updated_at: '',
});

function setup(inputs: Record<string, unknown> = {}) {
  const http = configureApiTest();
  const fixture = TestBed.createComponent(ProductList);
  for (const [k, v] of Object.entries(inputs)) fixture.componentRef.setInput(k, v);
  fixture.detectChanges();
  TestBed.tick();
  http.expectOne((r) => r.url === `${API}/categories/`).flush({ count: 1, next: null, previous: null, results: [{ id: 1, name: 'Keyboards', slug: 'keyboards' }] });
  return { http, fixture, el: fixture.nativeElement as HTMLElement };
}

describe('ProductList', () => {
  it('shows a loading state, then the products', async () => {
    const { http, fixture, el } = setup();
    expect(el.querySelector('mc-spinner')).not.toBeNull();

    http.expectOne((r) => r.url === `${API}/products/`).flush({ count: 2, next: null, previous: null, results: [product(1), product(2, 0)] });
    await fixture.whenStable();

    expect(el.querySelector('mc-spinner')).toBeNull();
    expect(el.querySelectorAll('.product').length).toBe(2);
    expect(text(el)).toContain('$129.00');
    expect(text(el)).toContain('Out of stock');
  });

  it('turns URL query params into API query params', () => {
    const { http } = setup({ search: 'mech', category: 'keyboards', ordering: 'price', page: '2' });
    const req = http.expectOne((r) => r.url === `${API}/products/`);
    const p = req.request.params;
    expect([p.get('search'), p.get('category'), p.get('ordering'), p.get('page'), p.get('page_size')]).toEqual([
      'mech', 'keyboards', 'price', '2', '12',
    ]);
  });

  it('ignores an unknown ordering instead of sending it to the API', () => {
    const { http } = setup({ ordering: 'password' });
    expect(http.expectOne((r) => r.url === `${API}/products/`).request.params.has('ordering')).toBe(false);
  });

  it('shows a friendly message and a retry button when the API fails', async () => {
    const { http, fixture, el } = setup();
    http.expectOne((r) => r.url === `${API}/products/`).flush('boom', { status: 500, statusText: 'Server Error' });
    await fixture.whenStable();

    expect(text(el.querySelector('mc-alert')!)).toContain('Something went wrong on the server. Please try again later.');
    el.querySelector<HTMLButtonElement>('mc-alert button')!.click();
    TestBed.tick();
    http.expectOne((r) => r.url === `${API}/products/`).flush({ count: 0, next: null, previous: null, results: [] });
    await fixture.whenStable();
    expect(text(el)).toContain('No products found');
  });
});
