import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';

import { AuthService } from '../auth/auth.service';
import { API_BASE_URL } from './api.config';

/** Endpoints that authenticate with a body (credentials / refresh token), never with a Bearer header. */
const AUTH_ENDPOINTS = ['/auth/login/', '/auth/register/', '/auth/refresh/'];

function withBearer(req: HttpRequest<unknown>, token: string): HttpRequest<unknown> {
  return req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
}

/**
 * The one HTTP interceptor (≈ a DelegatingHandler on HttpClient in .NET):
 *  1. attaches `Authorization: Bearer <access>` to requests for OUR API only;
 *  2. on 401 for a request that carried a token: refresh once, retry once;
 *  3. if the refresh fails: log out and send the user to /login.
 *
 * No loops: auth endpoints are never refreshed/retried, and the retried request goes
 * straight to the next handler, so a second 401 is simply returned to the caller.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const api = inject(API_BASE_URL);
  if (!req.url.startsWith(api) || AUTH_ENDPOINTS.some((path) => req.url.startsWith(api + path))) {
    return next(req); // other origins never see our token; auth endpoints need none
  }

  const auth = inject(AuthService);
  const router = inject(Router);
  const token = auth.accessToken();

  return next(token ? withBearer(req, token) : req).pipe(
    catchError((error: unknown) => {
      if (!(error instanceof HttpErrorResponse) || error.status !== 401 || !token) {
        return throwError(() => error);
      }
      return auth.refreshAccessToken().pipe(
        catchError(() => {
          auth.logout();
          void router.navigate(['/login'], { queryParams: { returnUrl: router.url } });
          return throwError(() => error);
        }),
        switchMap((newToken) => next(withBearer(req, newToken))),
      );
    }),
  );
};
