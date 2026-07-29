import Image from "next/image";
import Link from "next/link";
import { redirect } from "next/navigation";

import { CheckoutLink } from "@/components/checkout-link";
import { StoreHeader } from "@/components/store-header";
import { getCurrentUser } from "@/lib/auth-server";
import { getCart } from "@/lib/cart-server";
import { formatPrice } from "@/lib/format";


export const dynamic = "force-dynamic";

type RawSearchParams = Record<
  string,
  string | string[] | undefined
>;

interface CartPageProps {
  searchParams: Promise<RawSearchParams>;
}


function getFirstValue(
  value: string | string[] | undefined,
): string | undefined {
  return Array.isArray(value)
    ? value[0]
    : value;
}


export default async function CartPage({
  searchParams,
}: CartPageProps) {
  const currentUser = await getCurrentUser();

  if (!currentUser) {
    redirect("/login?next=/cart");
  }

  const [cart, params] = await Promise.all([
    getCart(),
    searchParams,
  ]);

  const message = getFirstValue(
    params.message,
  );

  const error = getFirstValue(params.error);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <StoreHeader />

      <section className="mx-auto max-w-7xl px-6 py-12">
        <div className="flex flex-wrap items-end justify-between gap-5">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
              Customer cart
            </p>

            <h1 className="mt-2 text-4xl font-bold tracking-tight">
              Your shopping cart
            </h1>
          </div>

          <Link
            href="/#catalogue"
            className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold transition hover:border-slate-950"
          >
            Continue shopping
          </Link>
        </div>

        {message ? (
          <div className="mt-8 rounded-xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-emerald-700">
            {message}
          </div>
        ) : null}

        {error ? (
          <div className="mt-8 rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-red-700">
            {error}
          </div>
        ) : null}

        {!cart ? (
          <div className="mt-10 rounded-2xl border border-red-200 bg-white p-8">
            <h2 className="text-xl font-bold">
              Cart unavailable
            </h2>

            <p className="mt-3 text-slate-600">
              The cart service could not be reached.
              Confirm that FastAPI is running.
            </p>
          </div>
        ) : cart.items.length === 0 ? (
          <div className="mt-10 rounded-3xl border border-slate-200 bg-white p-12 text-center shadow-sm">
            <h2 className="text-2xl font-bold">
              Your cart is empty
            </h2>

            <p className="mt-3 text-slate-600">
              Browse the catalogue and add a product
              to begin your order.
            </p>

            <Link
              href="/#catalogue"
              className="mt-7 inline-block rounded-xl bg-slate-950 px-6 py-3 font-semibold text-white"
            >
              Browse products
            </Link>
          </div>
        ) : (
          <div className="mt-10 grid gap-8 lg:grid-cols-[1fr_360px]">
            <section className="space-y-4">
              {cart.items.map((item) => (
                <article
                  key={item.id}
                  className="grid gap-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:grid-cols-[120px_1fr]"
                >
                  <div className="relative aspect-square overflow-hidden rounded-xl bg-slate-100">
                    {item.product.image_url ? (
                      <Image
                        src={item.product.image_url}
                        alt={item.product.name}
                        fill
                        sizes="120px"
                        className="object-cover"
                      />
                    ) : (
                      <div className="flex h-full items-center justify-center text-xs text-slate-400">
                        No image
                      </div>
                    )}
                  </div>

                  <div>
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <Link
                          href={`/products/${item.product.id}`}
                          className="text-lg font-bold hover:underline"
                        >
                          {item.product.name}
                        </Link>

                        <p className="mt-1 text-sm text-slate-500">
                          {item.product.brand}
                        </p>
                      </div>

                      <p className="text-lg font-bold">
                        {formatPrice(item.line_total)}
                      </p>
                    </div>

                    <p className="mt-3 text-sm text-slate-600">
                      {formatPrice(item.unit_price)} each
                    </p>

                    <p className="mt-1 text-xs text-slate-500">
                      {item.available_quantity} currently
                      available
                    </p>

                    <div className="mt-5 flex flex-wrap items-end gap-3">
                      <form
                        action="/api/cart"
                        method="post"
                        className="flex items-end gap-3"
                      >
                        <input
                          type="hidden"
                          name="action"
                          value="update"
                        />

                        <input
                          type="hidden"
                          name="item_id"
                          value={item.id}
                        />

                        <input
                          type="hidden"
                          name="return_to"
                          value="/cart"
                        />

                        <label>
                          <span className="mb-1 block text-xs font-medium text-slate-600">
                            Quantity
                          </span>

                          <input
                            name="quantity"
                            type="number"
                            min={1}
                            max={item.available_quantity}
                            defaultValue={item.quantity}
                            required
                            className="w-24 rounded-lg border border-slate-300 px-3 py-2"
                          />
                        </label>

                        <button
                          type="submit"
                          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold transition hover:border-slate-950"
                        >
                          Update
                        </button>
                      </form>

                      <form
                        action="/api/cart"
                        method="post"
                      >
                        <input
                          type="hidden"
                          name="action"
                          value="remove"
                        />

                        <input
                          type="hidden"
                          name="item_id"
                          value={item.id}
                        />

                        <input
                          type="hidden"
                          name="return_to"
                          value="/cart"
                        />

                        <button
                          type="submit"
                          className="rounded-lg px-4 py-2 text-sm font-semibold text-red-600 transition hover:bg-red-50"
                        >
                          Remove
                        </button>
                      </form>
                    </div>
                  </div>
                </article>
              ))}
            </section>

            <aside className="h-fit rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
              <h2 className="text-xl font-bold">
                Order summary
              </h2>

              <div className="mt-6 space-y-4 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-600">
                    Items
                  </span>

                  <span className="font-semibold">
                    {cart.total_quantity}
                  </span>
                </div>

                <div className="flex justify-between border-t border-slate-200 pt-4 text-lg">
                  <span className="font-semibold">
                    Subtotal
                  </span>

                  <span className="font-bold">
                    {formatPrice(cart.subtotal)}
                  </span>
                </div>
              </div>

              <CheckoutLink />

              <form
                action="/api/cart"
                method="post"
                className="mt-4"
              >
                <input
                  type="hidden"
                  name="action"
                  value="clear"
                />

                <input
                  type="hidden"
                  name="return_to"
                  value="/cart"
                />

                <button
                  type="submit"
                  className="w-full rounded-xl px-5 py-3 text-sm font-semibold text-red-600 transition hover:bg-red-50"
                >
                  Clear cart
                </button>
              </form>
            </aside>
          </div>
        )}
      </section>
    </main>
  );
}
