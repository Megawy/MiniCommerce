import { TestBed } from '@angular/core/testing';

import { API, configureApiTest } from '../../testing';
import { CategoryService } from './category.service';
import { ProductService } from './product.service';

describe('ProductService / CategoryService', () => {
  it('sends only the query params that are set', () => {
    const http = configureApiTest();
    TestBed.inject(ProductService)
      .list({ search: 'keyboard', category: 'keyboards', ordering: '-price', page: 2, min_price: undefined })
      .subscribe();
    const req = http.expectOne((r) => r.url === `${API}/products/`);
    expect(req.request.params.keys().sort()).toEqual(['category', 'ordering', 'page', 'search']);
    expect(req.request.params.get('category')).toBe('keyboards'); // slug, as django-filter expects
    expect(req.request.params.get('page')).toBe('2');
    req.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('loads one product by id', () => {
    const http = configureApiTest();
    TestBed.inject(ProductService).get(7).subscribe();
    http.expectOne(`${API}/products/7/`).flush({});
  });

  it('unwraps the categories page', () => {
    const http = configureApiTest();
    let names: string[] = [];
    TestBed.inject(CategoryService).list().subscribe((cats) => (names = cats.map((c) => c.name)));
    http.expectOne(`${API}/categories/?page_size=100`).flush({ count: 1, next: null, previous: null, results: [{ name: 'Mice' }] });
    expect(names).toEqual(['Mice']);
  });
});
