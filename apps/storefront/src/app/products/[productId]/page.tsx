import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import { CustomerEventTracker } from "@/components/customer-event-tracker";
import { StoreHeader } from "@/components/store-header";
import { getProduct } from "@/lib/api";
import { formatPrice } from "@/lib/format";
import type { ProductDetailResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

interface ProductPageProps {
  params: Promise<{
    productId: string;
  }>;
}

async function loadProduct(
  productId: string,
): Promise<ProductDetailResponse | null | undefined> {
  try {
    return await getProduct(productId);
  } catch (error) {
    console.error("Failed to load product:", error);
    return undefined;
  }
}

function ProductUnavailable() {
  return (
    <main className="min-h-screen bg-slate-50">
      <StoreHeader />

      <div className="mx-auto flex max-w-7xl justify-center px-6 py-24">
        <div className="max-w-md rounded-2xl border border-red-200 bg-white p-8 text-center shadow-sm">
          <h1 className="text-2xl font-bold text-slate-950">
            Product unavailable
          </h1>

          <p className="mt-3 text-slate-600">
            The product service is currently unavailable.
            Confirm that FastAPI is running on port 8000.
          </p>

          <Link
            href="/"
            className="mt-6 inline-block rounded-xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white"
          >
            Return to catalogue
          </Link>
        </div>
      </div>
    </main>
  );
}

export default async function ProductPage({
  params,
}: ProductPageProps) {
  const { productId } = await params;
  const product = await loadProduct(productId);

  if (product === null) {
    notFound();
  }

  if (product === undefined) {
    return <ProductUnavailable />;
  }

  const primaryImage = product.images[0];
  const isDiscounted =
    product.discount_price !== null &&
    Number(product.discount_price) < Number(product.price);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <StoreHeader />

      <CustomerEventTracker
        dedupeKey={`product-view:${product.id}`}
        event={{
          event_type: "product_view",
          product_id: product.id,
          properties: {
            source: "product_detail",
            product_name: product.name,
            brand: product.brand,
            category: product.category.name,
            effective_price:
              product.effective_price,
          },
        }}
      />

      <div className="mx-auto max-w-7xl px-6 py-10">
        <Link
          href="/#catalogue"
          className="text-sm font-semibold text-slate-600 transition hover:text-slate-950"
        >
          ← Back to catalogue
        </Link>

        <div className="mt-8 grid gap-10 lg:grid-cols-2">
          <section>
            <div className="relative aspect-[4/3] overflow-hidden rounded-3xl border border-slate-200 bg-white">
              {primaryImage ? (
                <Image
                  src={primaryImage.image_url}
                  alt={primaryImage.alt_text ?? product.name}
                  fill
                  priority
                  sizes="(max-width: 1024px) 100vw, 50vw"
                  className="object-cover"
                />
              ) : (
                <div className="flex h-full items-center justify-center text-slate-400">
                  No image available
                </div>
              )}
            </div>

            {product.images.length > 1 && (
              <div className="mt-4 grid grid-cols-4 gap-3">
                {product.images.map((image) => (
                  <div
                    key={image.id}
                    className="relative aspect-square overflow-hidden rounded-xl border border-slate-200 bg-white"
                  >
                    <Image
                      src={image.image_url}
                      alt={image.alt_text ?? product.name}
                      fill
                      sizes="150px"
                      className="object-cover"
                    />
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
              {product.category.name}
            </p>

            <h1 className="mt-3 text-4xl font-bold tracking-tight">
              {product.name}
            </h1>

            <div className="mt-3 flex items-center gap-4">
              <p className="text-slate-500">
                {product.brand}
              </p>

              <span className="text-sm font-medium text-amber-600">
                ★ {Number(product.average_rating).toFixed(1)}
              </span>
            </div>

            <div className="mt-8">
              <p className="text-3xl font-bold">
                {formatPrice(product.effective_price)}
              </p>

              {isDiscounted && (
                <p className="mt-1 text-lg text-slate-400 line-through">
                  {formatPrice(product.price)}
                </p>
              )}
            </div>

            <p className="mt-8 leading-7 text-slate-600">
              {product.description ??
                "No product description is currently available."}
            </p>

            <div className="mt-8 rounded-2xl bg-slate-50 p-5">
              <div className="flex items-center justify-between">
                <span className="font-medium text-slate-700">
                  Availability
                </span>

                <span
                  className={
                    product.inventory.in_stock
                      ? "font-semibold text-emerald-700"
                      : "font-semibold text-red-600"
                  }
                >
                  {product.inventory.in_stock
                    ? "In stock"
                    : "Out of stock"}
                </span>
              </div>

              {product.inventory.in_stock && (
                <p className="mt-2 text-sm text-slate-500">
                  {product.inventory.available_quantity} units currently
                  available
                </p>
              )}
            </div>

            <form
              action="/api/cart"
              method="post"
              className="mt-8 grid gap-4 sm:grid-cols-[120px_1fr]"
            >
              <input
                type="hidden"
                name="action"
                value="add"
              />

              <input
                type="hidden"
                name="product_id"
                value={product.id}
              />

              <input
                type="hidden"
                name="return_to"
                value={`/products/${product.id}`}
              />

              <label>
                <span className="mb-2 block text-sm font-medium text-slate-700">
                  Quantity
                </span>

                <select
                  name="quantity"
                  defaultValue="1"
                  disabled={!product.inventory.in_stock}
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 disabled:bg-slate-100"
                >
                  {product.inventory.in_stock ? (
                    Array.from(
                      {
                        length: Math.min(
                          product.inventory.available_quantity,
                          5,
                        ),
                      },
                      (_, index) => index + 1,
                    ).map((quantity) => (
                      <option
                        key={quantity}
                        value={quantity}
                      >
                        {quantity}
                      </option>
                    ))
                  ) : (
                    <option>Unavailable</option>
                  )}
                </select>
              </label>

              <div>
                <span className="mb-2 block text-sm font-medium text-transparent">
                  Action
                </span>

                <button
                  type="submit"
                  disabled={!product.inventory.in_stock}
                  className={
                    product.inventory.in_stock
                      ? "w-full rounded-xl bg-slate-950 px-6 py-3 font-semibold text-white transition hover:bg-slate-800"
                      : "w-full cursor-not-allowed rounded-xl bg-slate-300 px-6 py-3 font-semibold text-slate-600"
                  }
                >
                  {product.inventory.in_stock
                    ? "Add to cart"
                    : "Out of stock"}
                </button>
              </div>
            </form>
          </section>
        </div>
      </div>
    </main>
  );
}
