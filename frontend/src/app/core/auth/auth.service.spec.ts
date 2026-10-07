import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { User } from '../../shared/models/user';
import { API_BASE_URL } from '../http/api.config';
import { AuthService } from './auth.service';

const API = 'http://api.test/api';
const JANE: User = { id: 1, email: 'jane@example.com', first_name: 'Jane', last_name: 'Doe' };

function setup() {
  TestBed.configureTestingModule({
    providers: [provideHttpClient(), provideHttpClientTesting(), { provide: API_BASE_URL, useValue: API }],
  });
  return { auth: TestBed.inject(AuthService), http: TestBed.inject(HttpTestingController) };
}

describe('AuthService', () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('starts anonymous when no tokens are stored', () => {
    const { auth } = setup();
    auth.restoreSession(); // nothing to restore -> no request (verify() checks)
    expect(auth.isAuthenticated()).toBe(false);
    expect(auth.user()).toBeNull();
  });

  it('restores a stored session and loads the current user', () => {
    localStorage.setItem('minicommerce.access', 'stored-access');
    const { auth, http } = setup();
    expect(auth.isAuthenticated()).toBe(true);

    auth.restoreSession();
    http.expectOne(`${API}/auth/me/`).flush(JANE);

    expect(auth.user()).toEqual(JANE);
  });

  it('login stores both tokens, loads the user and becomes authenticated', () => {
    const { auth, http } = setup();
    let result: User | undefined;
    auth.login({ email: JANE.email, password: 'pw' }).subscribe((u) => (result = u));

    const login = http.expectOne(`${API}/auth/login/`);
    expect(login.request.method).toBe('POST');
    expect(login.request.body).toEqual({ email: JANE.email, password: 'pw' });
    login.flush({ access: 'a1', refresh: 'r1' });
    http.expectOne(`${API}/auth/me/`).flush(JANE);

    expect(result).toEqual(JANE);
    expect(auth.isAuthenticated()).toBe(true);
    expect(auth.accessToken()).toBe('a1');
    expect(localStorage.getItem('minicommerce.access')).toBe('a1');
    expect(localStorage.getItem('minicommerce.refresh')).toBe('r1');
  });

  it('failed login leaves the user anonymous and stores nothing', () => {
    const { auth, http } = setup();
    let failed = false;
    auth.login({ email: JANE.email, password: 'wrong' }).subscribe({ error: () => (failed = true) });
    http.expectOne(`${API}/auth/login/`).flush({ detail: 'No active account' }, { status: 401, statusText: 'Unauthorized' });

    expect(failed).toBe(true);
    expect(auth.isAuthenticated()).toBe(false);
    expect(localStorage.length).toBe(0);
  });

  it('register creates the account, then logs in', () => {
    const { auth, http } = setup();
    auth.register({ email: JANE.email, password: 'pw-12345678', first_name: 'Jane', last_name: 'Doe' }).subscribe();

    http.expectOne(`${API}/auth/register/`).flush(JANE, { status: 201, statusText: 'Created' });
    http.expectOne(`${API}/auth/login/`).flush({ access: 'a1', refresh: 'r1' });
    http.expectOne(`${API}/auth/me/`).flush(JANE);

    expect(auth.isAuthenticated()).toBe(true);
  });

  it('logout clears tokens and user', () => {
    localStorage.setItem('minicommerce.access', 'a1');
    localStorage.setItem('minicommerce.refresh', 'r1');
    const { auth } = setup();

    auth.logout();

    expect(auth.isAuthenticated()).toBe(false);
    expect(auth.user()).toBeNull();
    expect(localStorage.getItem('minicommerce.access')).toBeNull();
    expect(localStorage.getItem('minicommerce.refresh')).toBeNull();
  });

  it('concurrent refreshes share a single request', () => {
    localStorage.setItem('minicommerce.access', 'old');
    localStorage.setItem('minicommerce.refresh', 'r1');
    const { auth, http } = setup();
    const results: string[] = [];

    auth.refreshAccessToken().subscribe((t) => results.push(t));
    auth.refreshAccessToken().subscribe((t) => results.push(t));
    const refresh = http.expectOne(`${API}/auth/refresh/`); // exactly one
    expect(refresh.request.body).toEqual({ refresh: 'r1' });
    refresh.flush({ access: 'new' });

    expect(results).toEqual(['new', 'new']);
    expect(auth.accessToken()).toBe('new');
    expect(localStorage.getItem('minicommerce.refresh')).toBe('r1'); // no rotation: refresh token kept
  });
});
