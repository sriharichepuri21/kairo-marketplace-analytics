export interface CategorySummary {
  id: string;
  name: string;
  slug: string;
}

export interface CategoryResponse extends CategorySummary {
  product_count: number;
}

export interface ProductImage {
  id: string;
  image_url: string;
  alt_text: string | null;
  display_order: number;
}

export interface Inventory {
  available_quantity: number;
  reserved_quantity: number;
  in_stock: boolean;
}

export interface ProductListItem {
  id: string;
  name: string;
  slug: string;
  brand: string;
  price: string;
  discount_price: string | null;
  effective_price: string;
  average_rating: string;
  image_url: string | null;
  available_quantity: number;
  in_stock: boolean;
  category: CategorySummary;
}

export interface ProductDetailResponse {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  brand: string;
  price: string;
  discount_price: string | null;
  effective_price: string;
  average_rating: string;
  is_active: boolean;
  category: CategorySummary;
  images: ProductImage[];
  inventory: Inventory;
}

export interface ProductPageResponse {
  items: ProductListItem[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export type ProductSort =
  | "newest"
  | "price_asc"
  | "price_desc"
  | "rating_desc"
  | "name_asc";

export interface ProductFilters {
  search?: string;
  category?: string;
  brand?: string;
  minPrice?: string;
  maxPrice?: string;
  inStock?: boolean;
  sort?: ProductSort;
  page?: number;
  pageSize?: number;
}
