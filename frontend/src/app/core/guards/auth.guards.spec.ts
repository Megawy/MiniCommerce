import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot, UrlTree, provideRouter } from '@angular/router';

import { AuthService } from '../auth/auth.service';
import { authGuard, guestGuard } from './auth.guards';

function run(guard: typeof authGuard, authenticated: boolean, url = '/cart') {
  TestBed.configureTestingModule({
    providers: [provideRouter([]), { provide: AuthService, useValue: { isAuthenticated: () => authenticated } }],
  });
  const state = { url } as RouterStateSnapshot;
  return TestBed.runInInjectionContext(() => guard({} as ActivatedRouteSnapshot, state));
}

describe('authGuard', () => {
  it('lets authenticated users through', () => {
    expect(run(authGuard, true)).toBe(true);
  });

  it('redirects anonymous users to /login with a returnUrl', () => {
    const result = run(authGuard, false, '/orders/7');
    expect(result).toBeInstanceOf(UrlTree);
    expect(TestBed.inject(Router).serializeUrl(result as UrlTree)).toBe('/login?returnUrl=%2Forders%2F7');
  });
});

describe('guestGuard', () => {
  it('lets anonymous users see login/register', () => {
    expect(run(guestGuard, false)).toBe(true);
  });

  it('sends authenticated users home', () => {
    const result = run(guestGuard, true);
    expect(TestBed.inject(Router).serializeUrl(result as UrlTree)).toBe('/');
  });
});
