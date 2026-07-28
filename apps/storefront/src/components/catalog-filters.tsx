import Link from "next/link";

import type {
  CategoryResponse,
  ProductFilters,
} from "@/lib/types";

interface CatalogueFiltersProps {
  categories: CategoryResponse[];
  filters: ProductFilters;
}

export function CatalogueFilters({
  categories,
  filters,
}: CatalogueFiltersProps) {
  return (
    <form
      method="GET"
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-6">
        <label className="lg:col-span-2">
          <span className="mb-2 block text-sm font-medium text-slate-700">
            Search
          </span>

          <input
            type="search"
            name="search"
            defaultValue={filters.search}
            placeholder="Search products or brands"
            className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-slate-950"
          />
        </label>

        <label>
          <span className="mb-2 block text-sm font-medium text-slate-700">
            Category
          </span>

          <select
            name="category"
            defaultValue={filters.category ?? ""}
            className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none transition focus:border-slate-950"
          >
            <option value="">All categories</option>

            {categories.map((category) => (
              <option
                key={category.id}
                value={category.slug}
              >
                {category.name} ({category.product_count})
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className="mb-2 block text-sm font-medium text-slate-700">
            Minimum price
          </span>

          <input
            type="number"
            name="min_price"
            min="0"
            step="1"
            defaultValue={filters.minPrice}
            placeholder="₹0"
            className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-slate-950"
          />
        </label>

        <label>
          <span className="mb-2 block text-sm font-medium text-slate-700">
            Maximum price
          </span>

          <input
            type="number"
            name="max_price"
            min="0"
            step="1"
            defaultValue={filters.maxPrice}
            placeholder="No limit"
            className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-slate-950"
          />
        </label>

        <label>
          <span className="mb-2 block text-sm font-medium text-slate-700">
            Sort
          </span>

          <select
            name="sort"
            defaultValue={filters.sort ?? "rating_desc"}
            className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none transition focus:border-slate-950"
          >
            <option value="rating_desc">Highest rated</option>
            <option value="price_asc">Price: low to high</option>
            <option value="price_desc">Price: high to low</option>
            <option value="name_asc">Name: A to Z</option>
            <option value="newest">Newest</option>
          </select>
        </label>
      </div>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
        <label className="flex items-center gap-3 text-sm font-medium text-slate-700">
          <input
            type="checkbox"
            name="in_stock"
            value="true"
            defaultChecked={filters.inStock}
            className="h-4 w-4 rounded border-slate-300"
          />

          Show in-stock products only
        </label>

        <div className="flex gap-3">
          <Link
            href="/"
            className="rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            Reset
          </Link>

          <button
            type="submit"
            className="rounded-xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            Apply filters
          </button>
        </div>
      </div>
    </form>
  );
}
