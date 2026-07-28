import Image from "next/image";

import { getProducts } from "@/lib/api";
import type {
  ProductListItem,
  ProductPageResponse,
} from "@/lib/types";

export const dynamic = "force-dynamic";


function formatPrice(value: string): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(value));
}


function ProductCard({
  product,
}: {
  product: ProductListItem;
}) {
  const isDiscounted =
    product.discount_price !== null &&
    Number(product.discount_price) < Number(product.price);

  return (
    <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:-translate-y-1 hover:shadow-lg">
      <div className="relative aspect-[4/3] bg-slate-100">
        {product.image_url ? (
          <Image
            src={product.image_url}
            alt={product.name}
            fill
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
            className="object-cover"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-slate-400">
            No image available
          </div>
        )}

        {isDiscounted && (
          <span className="absolute left-3 top-3 rounded-full bg-slate-950 px-3 py-1 text-xs font-semibold text-white">
            Sale
          </span>
        )}
      </div>

      <div className="p-5">
        <div className="mb-2 flex items-center justify-between gap-3">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {product.category.name}
          </span>

          <span className="text-sm font-medium text-amber-600">
            ★ {Number(product.average_rating).toFixed(1)}
          </span>
        </div>

        <h2 className="min-h-14 text-lg font-semibold leading-7 text-slate-950">
          {product.name}
        </h2>

        <p className="mt-1 text-sm text-slate-500">
          {product.brand}
        </p>

        <div className="mt-5 flex items-end justify-between gap-4">
          <div>
            <p className="text-xl font-bold text-slate-950">
              {formatPrice(product.effective_price)}
            </p>

            {isDiscounted && (
              <p className="text-sm text-slate-400 line-through">
                {formatPrice(product.price)}
              </p>
            )}
          </div>

          <span
            className={
              product.in_stock
                ? "text-sm font-medium text-emerald-700"
                : "text-sm font-medium text-red-600"
            }
          >
            {product.in_stock
              ? `${product.available_quantity} available`
              : "Out of stock"}
          </span>
        </div>
      </div>
    </article>
  );
}


async function loadCatalogue(): Promise<ProductPageResponse | null> {
  try {
    return await getProducts(1, 12);
  } catch (error) {
    console.error("Failed to load catalogue:", error);
    return null;
  }
}


function CatalogueUnavailable() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
      <div className="max-w-md rounded-2xl border border-red-200 bg-white p-8 text-center shadow-sm">
        <h1 className="text-2xl font-bold text-slate-950">
          Catalogue unavailable
        </h1>

        <p className="mt-3 text-slate-600">
          The storefront could not connect to the Kairo API.
          Confirm that FastAPI is running on port 8000.
        </p>
      </div>
    </main>
  );
}


export default async function Home() {
  const catalogue = await loadCatalogue();

  if (catalogue === null) {
    return <CatalogueUnavailable />;
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div>
            <p className="text-2xl font-bold tracking-tight">
              Kairo
            </p>

            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
              Marketplace
            </p>
          </div>

          <nav className="flex items-center gap-6 text-sm font-medium text-slate-600">
            <span>Shop</span>
            <span>Categories</span>
            <span>Orders</span>
            <span>Cart</span>
          </nav>
        </div>
      </header>

      <section className="border-b border-slate-200 bg-slate-950 text-white">
        <div className="mx-auto max-w-7xl px-6 py-16">
          <p className="mb-4 text-sm font-semibold uppercase tracking-[0.24em] text-slate-300">
            Technology for everyday life
          </p>

          <h1 className="max-w-3xl text-4xl font-bold tracking-tight sm:text-6xl">
            Discover products built around how you work and live.
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
            Browse electronics, wearables, home products, gaming
            equipment, and accessories from the Kairo marketplace.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-12">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500">
              Featured catalogue
            </p>

            <h2 className="mt-1 text-3xl font-bold tracking-tight">
              Recommended products
            </h2>
          </div>

          <p className="text-sm text-slate-500">
            {catalogue.total_items} products
          </p>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {catalogue.items.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
            />
          ))}
        </div>
      </section>
    </main>
  );
}
