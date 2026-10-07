import { HttpClient, HttpErrorResponse, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import { AuthService } from '../auth/auth.service';
import { API_BASE_URL } from './api.config';
import { authInterceptor } from './auth.interceptor';

const API = 'http://api.test/api';
const UNAUTHORIZED = { status: 401, statusText: 'Unauthorized' };

function setup(tokens: { access?: string; refresh?: string } = {}) {
  localStorage.clear();
  if (tokens.access) localStorage.setItem('minicommerce.access', tokens.access);
  if (tokens.refresh) localStorage.setItem('minicommerce.refresh', tokens.refresh);
  TestBed.configureTestingModule({
    providers: [
      provideHttpClient(withInterceptors([authInterceptor])),
      provideHttpClientTesting(),
      provideRouter([]),
      { provide: API_BASE_URL, useValue: API },
    ],
  });
  return {
    client: TestBed.inject(HttpClient),
    http: TestBed.inject(HttpTestingController),
    auth: TestBed.inject(AuthService),
    router: TestBed.inject(Router),
  };
}

describe('authInterceptor', () => {
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('attaches the Bearer token to API requests', () => {
    const { client, http } = setup({ access: 'a1' });
    client.get(`${API}/cart/`).subscribe();
    const req = http.expectOne(`${API}/cart/`);
    expect(req.request.headers.get('Authorization')).toBe('Bearer a1');
    req.flush({});
  });

  it('sends no Authorization header when anonymous', () => {
    const { client, http } = setup();
    client.get(`${API}/products/`).subscribe();
    const req = http.expectOne(`${API}/products/`);
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({});
  });

  it('never sends the token to other origins', () => {
    const { client, http } = setup({ access: 'a1' });
    client.get('https://cdn.example.com/data.json').subscribe();
    const req = http.expectOne('https://cdn.example.com/data.json');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({});
  });

  it('does not attach the token to auth endpoints', () => {
    const { client, http } = setup({ access: 'a1' });
    client.post(`${API}/auth/login/`, {}).subscribe();
    const req = http.expectOne(`${API}/auth/login/`);
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({});
  });

  it('on 401 refreshes the access token and retries once', () => {
    const { client, http, auth } = setup({ access: 'expired', refresh: 'r1' });
    let body: unknown;
    client.get(`${API}/cart/`).subscribe((b) => (body = b));

    http.expectOne(`${API}/cart/`).flush({ detail: 'Token expired' }, UNAUTHORIZED);
    http.expectOne(`${API}/auth/refresh/`).flush({ access: 'fresh' });
    const retry = http.expectOne(`${API}/cart/`);
    expect(retry.request.headers.get('Authorization')).toBe('Bearer fresh');
    retry.flush({ id: 1, items: [], total: '0.00' });

    expect(body).toEqual({ id: 1, items: [], total: '0.00' });
    expect(auth.accessToken()).toBe('fresh');
  });

  it('two requests failing together trigger only one refresh', () => {
    const { client, http } = setup({ access: 'expired', refresh: 'r1' });
    client.get(`${API}/cart/`).subscribe();
    client.get(`${API}/orders/`).subscribe();

    http.expectOne(`${API}/cart/`).flush(null, UNAUTHORIZED);
    http.expectOne(`${API}/orders/`).flush(null, UNAUTHORIZED);
    http.expectOne(`${API}/auth/refresh/`).flush({ access: 'fresh' }); // exactly one
    http.expectOne(`${API}/cart/`).flush({});
    http.expectOne(`${API}/orders/`).flush({});
  });

  it('does not loop: a retried request that still gets 401 is returned as an error', () => {
    const { client, http } = setup({ access: 'expired', refresh: 'r1' });
    let error: HttpErrorResponse | undefined;
    client.get(`${API}/cart/`).subscribe({ error: (e) => (error = e) });

    http.expectOne(`${API}/cart/`).flush(null, UNAUTHORIZED);
    http.expectOne(`${API}/auth/refresh/`).flush({ access: 'fresh' });
    http.expectOne(`${API}/cart/`).flush(null, UNAUTHORIZED);

    http.expectNone(`${API}/auth/refresh/`);
    expect(error?.status).toBe(401);
  });

  it('logs out and redirects to /login when the refresh fails', () => {
    const { client, http, auth, router } = setup({ access: 'expired', refresh: 'expired-too' });
    const navigate = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    let error: HttpErrorResponse | undefined;
    client.get(`${API}/orders/`).subscribe({ error: (e) => (error = e) });

    http.expectOne(`${API}/orders/`).flush(null, UNAUTHORIZED);
    http.expectOne(`${API}/auth/refresh/`).flush({ detail: 'Token is invalid' }, UNAUTHORIZED);

    expect(error?.status).toBe(401);
    expect(auth.isAuthenticated()).toBe(false);
    expect(localStorage.getItem('minicommerce.refresh')).toBeNull();
    expect(navigate).toHaveBeenCalledWith(['/login'], expect.objectContaining({ queryParams: expect.any(Object) }));
  });

  it('does not try to refresh for anonymous 401s', () => {
    const { client, http } = setup();
    client.get(`${API}/cart/`).subscribe({ error: () => undefined });
    http.expectOne(`${API}/cart/`).flush(null, UNAUTHORIZED);
    http.expectNone(`${API}/auth/refresh/`);
  });
});
