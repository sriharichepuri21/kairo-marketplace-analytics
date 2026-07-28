import Image from "next/image";
import Link from "next/link";

import { formatPrice } from "@/lib/format";
import type { ProductListItem } from "@/lib/types";

interface ProductCardProps {
  product: ProductListItem;
}

export function ProductCard({
  product,
}: ProductCardProps) {
  const isDiscounted =
    product.discount_price !== null &&
    Number(product.discount_price) < Number(product.price);

  return (
    <Link
      href={`/products/${product.id}`}
      className="group block"
    >
      <article className="h-full overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition duration-200 group-hover:-translate-y-1 group-hover:shadow-lg">
        <div className="relative aspect-[4/3] bg-slate-100">
          {product.image_url ? (
            <Image
              src={product.image_url}
              alt={product.name}
              fill
              sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
              className="object-cover transition duration-300 group-hover:scale-[1.02]"
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
    </Link>
  );
}
