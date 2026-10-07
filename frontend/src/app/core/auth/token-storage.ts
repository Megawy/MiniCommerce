import { Injectable } from '@angular/core';

const ACCESS_KEY = 'minicommerce.access';
const REFRESH_KEY = 'minicommerce.refresh';

/**
 * Where JWTs live in the browser. One small class so the strategy can change in one place.
 *
 * Learning-project choice: localStorage (survives reloads, simple). Trade-off: any script
 * running on the page (an XSS bug, a compromised dependency) can read it. Production
 * alternatives: access token in memory + refresh token in an HttpOnly, Secure, SameSite
 * cookie set by the backend (needs backend changes). See README → Frontend → Token storage.
 */
@Injectable({ providedIn: 'root' })
export class TokenStorage {
  get access(): string | null {
    return this.read(ACCESS_KEY);
  }

  get refresh(): string | null {
    return this.read(REFRESH_KEY);
  }

  save(tokens: { access: string; refresh?: string }): void {
    this.write(ACCESS_KEY, tokens.access);
    if (tokens.refresh) this.write(REFRESH_KEY, tokens.refresh);
  }

  clear(): void {
    try {
      localStorage.removeItem(ACCESS_KEY);
      localStorage.removeItem(REFRESH_KEY);
    } catch {
      /* storage unavailable (private mode, blocked): nothing to clear */
    }
  }

  private read(key: string): string | null {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  }

  private write(key: string, value: string): void {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* storage unavailable: the session lasts until reload */
    }
  }
}
