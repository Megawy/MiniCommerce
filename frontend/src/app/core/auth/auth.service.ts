import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, finalize, map, shareReplay, switchMap, tap, throwError } from 'rxjs';

import { LoginRequest, RefreshResponse, RegisterRequest, TokenPair, User } from '../../shared/models/user';
import { API_BASE_URL } from '../http/api.config';
import { TokenStorage } from './token-storage';

/**
 * Authentication state + calls to the Django JWT endpoints.
 *
 * State lives in signals: components read `isAuthenticated()` / `user()` and re-render
 * automatically. "Authenticated" means "we hold an access token"; the user profile
 * (/api/auth/me/) is loaded separately and may arrive a moment later.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly storage = inject(TokenStorage);
  private readonly api = inject(API_BASE_URL);

  private readonly accessTokenSignal = signal<string | null>(this.storage.access);
  private readonly userSignal = signal<User | null>(null);
  private refreshInFlight: Observable<string> | null = null;

  readonly user = this.userSignal.asReadonly();
  readonly isAuthenticated = computed(() => this.accessTokenSignal() !== null);

  /** Current access token (read by the HTTP interceptor). */
  accessToken(): string | null {
    return this.accessTokenSignal();
  }

  /** Called once at startup: if tokens survived a reload, fetch the profile in the background. */
  restoreSession(): void {
    if (this.isAuthenticated()) {
      this.loadCurrentUser().subscribe({ error: () => undefined }); // 401 handled by the interceptor
    }
  }

  login(credentials: LoginRequest): Observable<User> {
    return this.http.post<TokenPair>(`${this.api}/auth/login/`, credentials).pipe(
      tap((tokens) => this.setTokens(tokens)),
      switchMap(() => this.loadCurrentUser()),
    );
  }

  /** Register, then log in with the same credentials (the API does not return tokens on register). */
  register(data: RegisterRequest): Observable<User> {
    return this.http
      .post<User>(`${this.api}/auth/register/`, data)
      .pipe(switchMap(() => this.login({ email: data.email, password: data.password })));
  }

  loadCurrentUser(): Observable<User> {
    return this.http.get<User>(`${this.api}/auth/me/`).pipe(tap((user) => this.userSignal.set(user)));
  }

  /**
   * Exchange the refresh token for a new access token.
   * Concurrent callers share ONE request (several 401s at once must not trigger several refreshes).
   */
  refreshAccessToken(): Observable<string> {
    const refresh = this.storage.refresh;
    if (!refresh) return throwError(() => new Error('No refresh token'));
    if (!this.refreshInFlight) {
      this.refreshInFlight = this.http.post<RefreshResponse>(`${this.api}/auth/refresh/`, { refresh }).pipe(
        tap((tokens) => this.setTokens(tokens)),
        map((tokens) => tokens.access),
        finalize(() => (this.refreshInFlight = null)),
        shareReplay({ bufferSize: 1, refCount: false }),
      );
    }
    return this.refreshInFlight;
  }

  /** Forget everything locally. (SimpleJWT has no server-side logout without the blacklist app.) */
  logout(): void {
    this.storage.clear();
    this.accessTokenSignal.set(null);
    this.userSignal.set(null);
  }

  private setTokens(tokens: { access: string; refresh?: string }): void {
    this.storage.save(tokens);
    this.accessTokenSignal.set(tokens.access);
  }
}
