import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Provider } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { API_BASE_URL } from './core/http/api.config';
import { authInterceptor } from './core/http/auth.interceptor';

/** Shared spec setup: real interceptor + router, fake backend at API. Test-only file. */
export const API = 'http://api.test/api';

export function configureApiTest(options: { authenticated?: boolean; providers?: Provider[] } = {}) {
  localStorage.clear();
  if (options.authenticated) localStorage.setItem('minicommerce.access', 'test-access');
  TestBed.configureTestingModule({
    providers: [
      provideRouter([]),
      provideHttpClient(withInterceptors([authInterceptor])),
      provideHttpClientTesting(),
      { provide: API_BASE_URL, useValue: API },
      ...(options.providers ?? []),
    ],
  });
  return TestBed.inject(HttpTestingController);
}

export const text = (el: Element) => el.textContent?.replace(/\s+/g, ' ').trim() ?? '';
