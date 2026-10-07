import { Money } from './api';

/** GET /api/categories/ */
export interface Category {
  id: number;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
}

/** Category as embedded in a product. */
export type CategorySummary = Pick<Category, 'id' | 'name' | 'slug'>;

/** GET /api/products/, /api/products/{id}/ */
export interface Product {
  id: number;
  name: string;
  slug: string;
  description: string;
  price: Money;
  stock: number;
  is_active: boolean;
  category: CategorySummary;
  created_at: string;
  updated_at: string;
}

/** Query parameters supported by GET /api/products/ */
export interface ProductQuery {
  category?: string; // category slug
  search?: string;
  min_price?: number;
  max_price?: number;
  ordering?: 'price' | '-price' | 'created_at' | '-created_at' | 'name' | '-name';
  page?: number;
  page_size?: number;
}
