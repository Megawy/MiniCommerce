import { InjectionToken } from '@angular/core';
import { environment } from '../../../environments/environment';

/** The single place the API base URL comes from (no hardcoded URLs in services). */
export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL', {
  providedIn: 'root',
  factory: () => environment.apiBaseUrl.replace(/\/$/, ''),
});
