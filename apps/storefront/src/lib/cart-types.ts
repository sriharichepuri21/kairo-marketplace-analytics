export interface CartProduct {
  id: string;
  name: string;
  slug: string;
  brand: string;
  image_url: string | null;
}

export interface CartItem {
  id: string;
  product: CartProduct;
  quantity: number;
  unit_price: string;
  line_total: string;
  available_quantity: number;
}

export interface Cart {
  id: string;
  user_id: string;
  items: CartItem[];
  total_quantity: number;
  subtotal: string;
  created_at: string;
  updated_at: string;
}
