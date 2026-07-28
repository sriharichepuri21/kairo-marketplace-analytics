export interface CategorySummary {
  id: string;
  name: string;
  slug: string;
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

export interface ProductPageResponse {
  items: ProductListItem[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}
