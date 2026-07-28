import { CatalogueFilters } from "@/components/catalog-filters";
import { Pagination } from "@/components/pagination";
import { ProductCard } from "@/components/product-card";
import { StoreHeader } from "@/components/store-header";
import {
  getCategories,
  getProducts,
} from "@/lib/api";
import type {
  CategoryResponse,
  ProductFilters,
  ProductPageResponse,
  ProductSort,
} from "@/lib/types";

export const dynamic = "force-dynamic";

type RawSearchParams = Record<
  string,
  string | string[] | undefined
>;

interface HomePageProps {
  searchParams: Promise<RawSearchParams>;
}

interface CatalogueData {
  catalogue: ProductPageResponse;
  categories: CategoryResponse[];
}

const validSorts = new Set<ProductSort>([
  "newest",
  "price_asc",
  "price_desc",
  "rating_desc",
  "name_asc",
]);

function getFirstValue(
  value: string | string[] | undefined,
): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function getPositivePage(
  value: string | undefined,
): number {
  const parsed = Number(value);

  if (!Number.isInteger(parsed) || parsed < 1) {
    return 1;
  }

  return parsed;
}

function getSort(
  value: string | undefined,
): ProductSort {
  if (value && validSorts.has(value as ProductSort)) {
    return value as ProductSort;
  }

  return "rating_desc";
}

function getFilters(
  searchParams: RawSearchParams,
): ProductFilters {
  return {
    search: getFirstValue(searchParams.search)?.trim() || undefined,
    category:
      getFirstValue(searchParams.category)?.trim() || undefined,
    brand: getFirstValue(searchParams.brand)?.trim() || undefined,
    minPrice:
      getFirstValue(searchParams.min_price)?.trim() || undefined,
    maxPrice:
      getFirstValue(searchParams.max_price)?.trim() || undefined,
    inStock:
      getFirstValue(searchParams.in_stock) === "true",
    sort: getSort(getFirstValue(searchParams.sort)),
    page: getPositivePage(getFirstValue(searchParams.page)),
    pageSize: 12,
  };
}

async function loadCatalogue(
  filters: ProductFilters,
): Promise<CatalogueData | null> {
  try {
    const [catalogue, categories] = await Promise.all([
      getProducts(filters),
      getCategories(),
    ]);

    return {
      catalogue,
      categories,
    };
  } catch (error) {
    console.error("Failed to load catalogue:", error);
    return null;
  }
}

function CatalogueUnavailable() {
  return (
    <main className="min-h-screen bg-slate-50">
      <StoreHeader />

      <div className="mx-auto flex max-w-7xl justify-center px-6 py-24">
        <div className="max-w-md rounded-2xl border border-red-200 bg-white p-8 text-center shadow-sm">
          <h1 className="text-2xl font-bold text-slate-950">
            Catalogue unavailable
          </h1>

          <p className="mt-3 text-slate-600">
            The storefront could not connect to the Kairo API.
            Confirm that FastAPI is running on port 8000.
          </p>
        </div>
      </div>
    </main>
  );
}

export default async function Home({
  searchParams,
}: HomePageProps) {
  const resolvedSearchParams = await searchParams;
  const filters = getFilters(resolvedSearchParams);
  const data = await loadCatalogue(filters);

  if (data === null) {
    return <CatalogueUnavailable />;
  }

  const { catalogue, categories } = data;

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <StoreHeader />

      <section className="border-b border-slate-200 bg-slate-950 text-white">
        <div className="mx-auto max-w-7xl px-6 py-16">
          <p className="mb-4 text-sm font-semibold uppercase tracking-[0.24em] text-slate-300">
            Technology for everyday life
          </p>

          <h1 className="max-w-3xl text-4xl font-bold tracking-tight sm:text-6xl">
            Discover products built around how you work and live.
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
            Search electronics, wearables, home products,
            gaming equipment, and accessories from the Kairo
            marketplace.
          </p>
        </div>
      </section>

      <section
        id="catalogue"
        className="mx-auto max-w-7xl scroll-mt-6 px-6 py-12"
      >
        <CatalogueFilters
          categories={categories}
          filters={filters}
        />

        <div className="mb-8 mt-10 flex items-end justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500">
              Product catalogue
            </p>

            <h2 className="mt-1 text-3xl font-bold tracking-tight">
              {filters.search
                ? `Results for “${filters.search}”`
                : "Explore products"}
            </h2>
          </div>

          <p className="text-sm text-slate-500">
            {catalogue.total_items} products
          </p>
        </div>

        {catalogue.items.length > 0 ? (
          <>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {catalogue.items.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                />
              ))}
            </div>

            <Pagination
              currentPage={catalogue.page}
              totalPages={catalogue.total_pages}
              filters={filters}
            />
          </>
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center">
            <h3 className="text-xl font-semibold text-slate-950">
              No products found
            </h3>

            <p className="mt-2 text-slate-600">
              Change or reset the current filters and try again.
            </p>
          </div>
        )}
      </section>
    </main>
  );
}
