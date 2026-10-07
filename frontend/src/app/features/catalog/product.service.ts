import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { API_BASE_URL } from '../../core/http/api.config';
import { Paginated } from '../../shared/models/api';
import { Product, ProductQuery } from '../../shared/models/catalog';

/** Catalog reads. Filtering, search, ordering and pagination all happen in Django. */
@Injectable({ providedIn: 'root' })
export class ProductService {
  private readonly http = inject(HttpClient);
  private readonly api = inject(API_BASE_URL);

  list(query: ProductQuery = {}): Observable<Paginated<Product>> {
    let params = new HttpParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== '') params = params.set(key, String(value));
    }
    return this.http.get<Paginated<Product>>(`${this.api}/products/`, { params });
  }

  get(id: number | string): Observable<Product> {
    return this.http.get<Product>(`${this.api}/products/${id}/`);
  }
}
