import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';

import { API, configureApiTest, text } from '../../../testing';
import { Login } from './login';

function setup(returnUrl?: string) {
  const http = configureApiTest();
  const fixture = TestBed.createComponent(Login);
  if (returnUrl) fixture.componentRef.setInput('returnUrl', returnUrl);
  fixture.detectChanges();
  const el = fixture.nativeElement as HTMLElement;
  const fill = (email: string, password: string) => {
    for (const [id, value] of [['email', email], ['password', password]]) {
      const input = el.querySelector<HTMLInputElement>(`#${id}`)!;
      input.value = value;
      input.dispatchEvent(new Event('input'));
    }
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
  };
  return { http, fixture, el, fill, router: TestBed.inject(Router) };
}

describe('Login page', () => {
  it('signs in and returns to the returnUrl', async () => {
    const { http, fixture, fill, router } = setup('/cart');
    const navigate = vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);

    fill('jane@example.com', 'secret');
    http.expectOne(`${API}/auth/login/`).flush({ access: 'a', refresh: 'r' });
    http.expectOne(`${API}/auth/me/`).flush({ id: 1, email: 'jane@example.com', first_name: '', last_name: '' });
    http.match(`${API}/cart/`); // CartService reacts to the new session; not under test here
    await fixture.whenStable();

    expect(navigate).toHaveBeenCalledWith('/cart');
  });

  it('shows "Incorrect email or password." on 401, not the session-expired text', async () => {
    const { http, fixture, el, fill } = setup();
    fill('jane@example.com', 'wrong');
    http
      .expectOne(`${API}/auth/login/`)
      .flush({ detail: 'No active account found with the given credentials' }, { status: 401, statusText: 'Unauthorized' });
    await fixture.whenStable();

    expect(text(el.querySelector('mc-alert')!)).toBe('Incorrect email or password.');
    expect(localStorage.getItem('minicommerce.access')).toBeNull();
  });
});
