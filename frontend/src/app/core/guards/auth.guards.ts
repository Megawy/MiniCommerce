import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from '../auth/auth.service';

/** Pages that need a logged-in user (≈ [Authorize]). Anonymous users go to /login and come back. */
export const authGuard: CanActivateFn = (_route, state) => {
  if (inject(AuthService).isAuthenticated()) return true;
  return inject(Router).createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
};

/** Login/register pages: already logged-in users are sent home. */
export const guestGuard: CanActivateFn = () => {
  if (!inject(AuthService).isAuthenticated()) return true;
  return inject(Router).createUrlTree(['/']);
};
