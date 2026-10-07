import { Routes } from '@angular/router';

import { authGuard, guestGuard } from './core/guards/auth.guards';
import { Shell } from './layout/shell/shell';

/** All pages render inside the Shell (header + main). Feature pages are lazy-loaded. */
export const routes: Routes = [
  {
    path: '',
    component: Shell,
    children: [
      {
        path: '',
        title: 'MiniCommerce',
        loadComponent: () => import('./features/catalog/home/home').then((m) => m.Home),
      },
      {
        path: 'products',
        loadChildren: () => import('./features/catalog/catalog.routes').then((m) => m.CATALOG_ROUTES),
      },
      {
        path: 'cart',
        title: 'Cart · MiniCommerce',
        canActivate: [authGuard],
        loadComponent: () => import('./features/cart/cart-page').then((m) => m.CartPage),
      },
      {
        path: 'orders',
        canActivate: [authGuard],
        loadChildren: () => import('./features/orders/orders.routes').then((m) => m.ORDERS_ROUTES),
      },
      {
        path: 'login',
        title: 'Log in · MiniCommerce',
        canActivate: [guestGuard],
        loadComponent: () => import('./features/auth/login/login').then((m) => m.Login),
      },
      {
        path: 'register',
        title: 'Create account · MiniCommerce',
        canActivate: [guestGuard],
        loadComponent: () => import('./features/auth/register/register').then((m) => m.Register),
      },
      {
        path: '**',
        title: 'Not found · MiniCommerce',
        loadComponent: () => import('./features/not-found/not-found').then((m) => m.NotFound),
      },
    ],
  },
];
