import type { ProductPageResponse } from "@/lib/types";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export async function getProducts(
  page = 1,
  pageSize = 12,
): Promise<ProductPageResponse> {
  const url = new URL("/api/v1/products", API_URL);

  url.searchParams.set("page", String(page));
  url.searchParams.set("page_size", String(pageSize));
  url.searchParams.set("sort", "rating_desc");

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
