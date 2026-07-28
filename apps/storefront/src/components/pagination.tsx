import Link from "next/link";

import type { ProductFilters } from "@/lib/types";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  filters: ProductFilters;
}

function createPageHref(
  page: number,
  filters: ProductFilters,
): string {
  const params = new URLSearchParams();

  if (filters.search) {
    params.set("search", filters.search);
  }

  if (filters.category) {
    params.set("category", filters.category);
  }

  if (filters.brand) {
    params.set("brand", filters.brand);
  }

  if (filters.minPrice) {
    params.set("min_price", filters.minPrice);
  }

  if (filters.maxPrice) {
    params.set("max_price", filters.maxPrice);
  }

  if (filters.inStock) {
    params.set("in_stock", "true");
  }

  if (filters.sort) {
    params.set("sort", filters.sort);
  }

  params.set("page", String(page));

  return `/?${params.toString()}#catalogue`;
}

export function Pagination({
  currentPage,
  totalPages,
  filters,
}: PaginationProps) {
  if (totalPages <= 1) {
    return null;
  }

  return (
    <nav className="mt-10 flex items-center justify-center gap-4">
      {currentPage > 1 ? (
        <Link
          href={createPageHref(currentPage - 1, filters)}
          className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
        >
          Previous
        </Link>
      ) : (
        <span className="cursor-not-allowed rounded-xl border border-slate-200 bg-slate-100 px-5 py-3 text-sm font-semibold text-slate-400">
          Previous
        </span>
      )}

      <span className="text-sm font-medium text-slate-600">
        Page {currentPage} of {totalPages}
      </span>

      {currentPage < totalPages ? (
        <Link
          href={createPageHref(currentPage + 1, filters)}
          className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
        >
          Next
        </Link>
      ) : (
        <span className="cursor-not-allowed rounded-xl border border-slate-200 bg-slate-100 px-5 py-3 text-sm font-semibold text-slate-400">
          Next
        </span>
      )}
    </nav>
  );
}
