import Link from "next/link";
import { redirect } from "next/navigation";

import { StoreHeader } from "@/components/store-header";
import { getAddresses } from "@/lib/address-server";
import { getCurrentUser } from "@/lib/auth-server";
import { getCart } from "@/lib/cart-server";
import { formatPrice } from "@/lib/format";


export const dynamic = "force-dynamic";

type RawSearchParams = Record<
  string,
  string | string[] | undefined
>;

interface CheckoutPageProps {
  searchParams: Promise<RawSearchParams>;
}


function getFirstValue(
  value: string | string[] | undefined,
): string | undefined {
  return Array.isArray(value)
    ? value[0]
    : value;
}


export default async function CheckoutPage({
  searchParams,
}: CheckoutPageProps) {
  const currentUser = await getCurrentUser();

  if (!currentUser) {
    redirect("/login?next=/checkout");
  }

  const [cart, addresses, params] =
    await Promise.all([
      getCart(),
      getAddresses(),
      searchParams,
    ]);

  if (cart && cart.items.length === 0) {
    redirect(
      "/cart?error=Your cart is empty.",
    );
  }

  const error = getFirstValue(
    params.error,
  );

  const defaultAddressId =
    addresses?.find(
      (address) => address.is_default,
    )?.id ?? addresses?.[0]?.id;

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <StoreHeader />

      <section className="mx-auto max-w-7xl px-6 py-12">
        <div className="flex flex-wrap items-end justify-between gap-5">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
              Secure checkout
            </p>

            <h1 className="mt-2 text-4xl font-bold tracking-tight">
              Review your order
            </h1>

            <p className="mt-3 text-slate-600">
              Select a delivery address and
              confirm your purchase.
            </p>
          </div>

          <Link
            href="/cart"
            className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold transition hover:border-slate-950"
          >
            Return to cart
          </Link>
        </div>

        {error ? (
          <div className="mt-8 rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-red-700">
            {error}
          </div>
        ) : null}

        {!cart || !addresses ? (
          <div className="mt-10 rounded-2xl border border-red-200 bg-white p-8">
            <h2 className="text-xl font-bold">
              Checkout unavailable
            </h2>

            <p className="mt-3 text-slate-600">
              The cart or address service could
              not be reached. Confirm that
              FastAPI is running.
            </p>
          </div>
        ) : (
          <div className="mt-10 grid gap-8 lg:grid-cols-[1fr_380px]">
            <section>
              <div className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h2 className="text-2xl font-bold">
                      Shipping address
                    </h2>

                    <p className="mt-2 text-sm text-slate-600">
                      Your order will be delivered
                      to the selected address.
                    </p>
                  </div>

                  <Link
                    href="/account/addresses"
                    className="text-sm font-semibold text-slate-700 underline-offset-4 hover:underline"
                  >
                    Manage addresses
                  </Link>
                </div>

                {addresses.length === 0 ? (
                  <div className="mt-7 rounded-2xl border border-amber-200 bg-amber-50 p-6">
                    <h3 className="font-bold text-amber-900">
                      Add a shipping address
                    </h3>

                    <p className="mt-2 text-sm leading-6 text-amber-800">
                      You need at least one saved
                      address before placing an
                      order.
                    </p>

                    <Link
                      href="/account/addresses"
                      className="mt-5 inline-block rounded-xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white"
                    >
                      Add shipping address
                    </Link>
                  </div>
                ) : (
                  <form
                    action="/api/checkout"
                    method="post"
                    className="mt-7"
                  >
                    <fieldset className="space-y-4">
                      <legend className="sr-only">
                        Select shipping address
                      </legend>

                      {addresses.map((address) => (
                        <label
                          key={address.id}
                          className="flex cursor-pointer gap-4 rounded-2xl border border-slate-200 p-5 transition hover:border-slate-950"
                        >
                          <input
                            type="radio"
                            name="shipping_address_id"
                            value={address.id}
                            defaultChecked={
                              address.id ===
                              defaultAddressId
                            }
                            required
                            className="mt-1 h-4 w-4"
                          />

                          <span className="flex-1">
                            <span className="flex flex-wrap items-center gap-3">
                              <span className="font-bold">
                                {address.full_name}
                              </span>

                              {address.is_default ? (
                                <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
                                  Default
                                </span>
                              ) : null}
                            </span>

                            <span className="mt-1 block text-sm text-slate-500">
                              {address.phone}
                            </span>

                            <span className="mt-3 block text-sm leading-6 text-slate-600">
                              {address.address_line_1}
                              <br />

                              {address.address_line_2 ? (
                                <>
                                  {
                                    address.address_line_2
                                  }
                                  <br />
                                </>
                              ) : null}

                              {address.city},{" "}
                              {address.state}{" "}
                              {address.postal_code}
                              <br />

                              {address.country_code}
                            </span>
                          </span>
                        </label>
                      ))}
                    </fieldset>

                    <label className="mt-7 block">
                      <span className="text-sm font-medium text-slate-700">
                        Delivery note
                      </span>

                      <span className="mt-1 block text-xs text-slate-500">
                        Optional, maximum 1,000
                        characters.
                      </span>

                      <textarea
                        name="customer_note"
                        rows={4}
                        maxLength={1000}
                        placeholder="Example: Leave the package with reception."
                        className="mt-3 w-full resize-y rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-950"
                      />
                    </label>

                    <div className="mt-7 rounded-2xl bg-slate-50 p-5 text-sm leading-6 text-slate-600">
                      Product prices and available
                      inventory are validated again
                      when the order is placed.
                    </div>

                    <button
                      type="submit"
                      className="mt-7 w-full rounded-xl bg-slate-950 px-6 py-4 font-semibold text-white transition hover:bg-slate-800"
                    >
                      Place order
                    </button>
                  </form>
                )}
              </div>
            </section>

            <aside className="h-fit rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
              <h2 className="text-xl font-bold">
                Order summary
              </h2>

              <div className="mt-6 space-y-5">
                {cart.items.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-start justify-between gap-4 border-b border-slate-100 pb-4"
                  >
                    <div>
                      <p className="text-sm font-semibold">
                        {item.product.name}
                      </p>

                      <p className="mt-1 text-xs text-slate-500">
                        Quantity {item.quantity}
                      </p>
                    </div>

                    <p className="text-sm font-semibold">
                      {formatPrice(
                        item.line_total,
                      )}
                    </p>
                  </div>
                ))}
              </div>

              <div className="mt-6 space-y-4 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-600">
                    Items
                  </span>

                  <span className="font-semibold">
                    {cart.total_quantity}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-slate-600">
                    Shipping
                  </span>

                  <span className="font-semibold">
                    {formatPrice("0.00")}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-slate-600">
                    Tax
                  </span>

                  <span className="font-semibold">
                    {formatPrice("0.00")}
                  </span>
                </div>

                <div className="flex justify-between border-t border-slate-200 pt-4 text-lg">
                  <span className="font-semibold">
                    Total
                  </span>

                  <span className="font-bold">
                    {formatPrice(
                      cart.subtotal,
                    )}
                  </span>
                </div>
              </div>
            </aside>
          </div>
        )}
      </section>
    </main>
  );
}
