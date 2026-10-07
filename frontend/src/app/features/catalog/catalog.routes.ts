import { Routes } from '@angular/router';

export const CATALOG_ROUTES: Routes = [
  {
    path: '',
    title: 'Products · MiniCommerce',
    loadComponent: () => import('./product-list/product-list').then((m) => m.ProductList),
  },
  {
    path: ':id',
    title: 'Product · MiniCommerce',
    loadComponent: () => import('./product-detail/product-detail').then((m) => m.ProductDetail),
  },
];
