export type OrderStatus =
  | "pending"
  | "confirmed"
  | "processing"
  | "shipped"
  | "delivered"
  | "cancelled";

export type PaymentStatus =
  | "pending"
  | "paid"
  | "failed"
  | "refunded";

export interface OrderShippingAddress {
  full_name: string;
  phone: string;
  address_line_1: string;
  address_line_2: string | null;
  city: string;
  state: string;
  postal_code: string;
  country_code: string;
}

export interface OrderItem {
  id: string;
  product_id: string | null;
  product_name: string;
  product_slug: string;
  product_brand: string;
  quantity: number;
  unit_price: string;
  line_total: string;
  created_at: string;
}

export interface OrderStatusHistory {
  id: string;
  status: OrderStatus;
  note: string | null;
  created_at: string;
}

export interface Order {
  id: string;
  order_number: string;
  user_id: string;
  status: OrderStatus;
  payment_status: PaymentStatus;
  currency_code: string;
  subtotal: string;
  shipping_amount: string;
  tax_amount: string;
  total_amount: string;
  shipping_address: OrderShippingAddress;
  customer_note: string | null;
  items: OrderItem[];
  status_history: OrderStatusHistory[];
  created_at: string;
  updated_at: string;
}
