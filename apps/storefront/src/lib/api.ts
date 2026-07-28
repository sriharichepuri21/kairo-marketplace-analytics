import type {
  CategoryResponse,
  ProductDetailResponse,
  ProductFilters,
  ProductPageResponse,
} from "@/lib/types";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

function createApiUrl(pathname: string): URL {
  return new URL(pathname, API_URL);
}

export async function getProducts(
  filters: ProductFilters = {},
): Promise<ProductPageResponse> {
  const url = createApiUrl("/api/v1/products");

  if (filters.search) {
    url.searchParams.set("search", filters.search);
  }

  if (filters.category) {
    url.searchParams.set("category", filters.category);
  }

  if (filters.brand) {
    url.searchParams.set("brand", filters.brand);
  }

  if (filters.minPrice) {
    url.searchParams.set("min_price", filters.minPrice);
  }

  if (filters.maxPrice) {
    url.searchParams.set("max_price", filters.maxPrice);
  }

  if (filters.inStock) {
    url.searchParams.set("in_stock", "true");
  }

  url.searchParams.set("sort", filters.sort ?? "rating_desc");
  url.searchParams.set("page", String(filters.page ?? 1));
  url.searchParams.set("page_size", String(filters.pageSize ?? 12));

  const response = await fetch(url, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(
      `Product request failed with status ${response.status}`,
    );
  }

  return response.json() as Promise<ProductPageResponse>;
}

export async function getCategories(): Promise<CategoryResponse[]> {
  const response = await fetch(
    createApiUrl("/api/v1/categories"),
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      `Category request failed with status ${response.status}`,
    );
  }

  return response.json() as Promise<CategoryResponse[]>;
}

export async function getProduct(
  productId: string,
): Promise<ProductDetailResponse | null> {
  const response = await fetch(
    createApiUrl(`/api/v1/products/${productId}`),
    {
      cache: "no-store",
    },
  );

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(
      `Product detail request failed with status ${response.status}`,
    );
  }

  return response.json() as Promise<ProductDetailResponse>;
}
