import { Money } from './api';
import { Product } from './catalog';

export type CartProduct = Pick<Product, 'id' | 'name' | 'slug' | 'price'>;

export interface CartItem {
  id: number;
  product: CartProduct;
  quantity: number;
  subtotal: Money;
}

/** GET /api/cart/ — total is computed by the server from current prices. */
export interface Cart {
  id: number;
  items: CartItem[];
  total: Money;
}

/** POST /api/cart/items/ */
export interface AddCartItemRequest {
  product_id: number;
  quantity: number;
}
