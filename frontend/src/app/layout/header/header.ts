import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import { ThemeService } from '../../core/services/theme.service';
import { CartService } from '../../features/cart/cart.service';

@Component({
  selector: 'mc-header',
  imports: [RouterLink, RouterLinkActive],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './header.html',
  styleUrl: './header.css',
})
export class Header {
  protected readonly auth = inject(AuthService);
  protected readonly theme = inject(ThemeService);
  /** Badge count; CartService loads the cart when a session starts and refreshes it after every change. */
  protected readonly cart = inject(CartService);
  private readonly router = inject(Router);

  /** Mobile navigation open/closed (local UI state → a signal). */
  protected readonly menuOpen = signal(false);

  protected logout(): void {
    this.auth.logout();
    this.menuOpen.set(false);
    void this.router.navigateByUrl('/');
  }
}
