import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter, withComponentInputBinding } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { routes } from './app.routes';
import { API_BASE_URL } from './core/http/api.config';
import { authInterceptor } from './core/http/auth.interceptor';

async function boot(url: string, authenticated = false) {
  localStorage.clear();
  if (authenticated) localStorage.setItem('minicommerce.access', 'a1');
  TestBed.configureTestingModule({
    providers: [
      provideRouter(routes, withComponentInputBinding()),
      provideHttpClient(withInterceptors([authInterceptor])),
      provideHttpClientTesting(),
      { provide: API_BASE_URL, useValue: 'http://api.test/api' },
    ],
  });
  const harness = await RouterTestingHarness.create(url);
  return { harness, el: harness.routeNativeElement as HTMLElement, router: TestBed.inject(Router) };
}

const navText = (el: HTMLElement) => el.querySelector('nav')?.textContent?.replace(/\s+/g, ' ') ?? '';

describe('Application shell & routing', () => {
  it('renders the shell with anonymous navigation', async () => {
    const { el } = await boot('/');
    expect(el.querySelector('mc-header')).not.toBeNull();
    expect(el.querySelector('main#main')).not.toBeNull();
    expect(navText(el)).toContain('Products');
    expect(navText(el)).toContain('Log in');
    expect(navText(el)).toContain('Register');
    expect(navText(el)).not.toContain('Orders');
  });

  it('shows cart, orders and logout when authenticated', async () => {
    const { el } = await boot('/', true);
    const text = navText(el);
    expect(text).toContain('Cart');
    expect(text).toContain('Orders');
    expect(text).toContain('Log out');
    expect(text).not.toContain('Log in');
  });

  it('redirects anonymous users from /cart to /login with returnUrl', async () => {
    const { harness, router } = await boot('/');
    await harness.navigateByUrl('/cart');
    expect(router.url).toBe('/login?returnUrl=%2Fcart');
    expect((harness.routeNativeElement as HTMLElement).querySelector('h1')?.textContent).toContain('Log in');
  });

  it('lazy-loads feature routes with route parameters', async () => {
    const { harness } = await boot('/', true);
    const page = await harness.navigateByUrl('/orders/42');
    // The :id param reached the lazy component: it requests exactly that order.
    TestBed.inject(HttpTestingController)
      .expectOne('http://api.test/api/orders/42/')
      .flush({ id: 42, status: 'PAID', total: '1.00', created_at: '', updated_at: '', items: [] });
    await harness.fixture.whenStable();
    expect((harness.routeNativeElement as HTMLElement).textContent).toContain('Order #42');
    expect(page).toBeTruthy();
  });

  it('renders the not-found page for unknown URLs', async () => {
    const { harness } = await boot('/');
    await harness.navigateByUrl('/does-not-exist');
    expect((harness.routeNativeElement as HTMLElement).querySelector('h1')?.textContent).toContain('Page not found');
  });
});
