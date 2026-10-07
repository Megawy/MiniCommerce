import { Money } from './api';
import { Product } from './catalog';

export type OrderStatus = 'PENDING' | 'PAID' | 'CANCELLED' | 'COMPLETED';

/** GET /api/orders/ (list rows have no items) */
export interface OrderSummary {
  id: number;
  status: OrderStatus;
  total: Money;
  created_at: string;
  updated_at: string;
}

export type OrderProduct = Pick<Product, 'id' | 'name' | 'slug'>;

export interface OrderItem {
  id: number;
  product: OrderProduct;
  quantity: number;
  price: Money; // price snapshot at checkout — not the product's current price
  subtotal: Money;
}

/** GET /api/orders/{id}/ and the 201 body of POST /api/orders/checkout/ */
export interface Order extends OrderSummary {
  items: OrderItem[];
}

// No Payment model here on purpose: the API does not expose payments (Django Admin only).
