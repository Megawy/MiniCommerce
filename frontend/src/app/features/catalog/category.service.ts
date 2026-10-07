import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { API_BASE_URL } from '../../core/http/api.config';
import { Paginated } from '../../shared/models/api';
import { Category } from '../../shared/models/catalog';

@Injectable({ providedIn: 'root' })
export class CategoryService {
  private readonly http = inject(HttpClient);
  private readonly api = inject(API_BASE_URL);

  /** All categories for the filter menu (a handful; one page of up to 100). */
  list(): Observable<Category[]> {
    return this.http
      .get<Paginated<Category>>(`${this.api}/categories/`, { params: { page_size: 100 } })
      .pipe(map((page) => page.results));
  }
}
