import Link from "next/link";
import {
  notFound,
  redirect,
} from "next/navigation";

import { StoreHeader } from "@/components/store-header";
import { getCurrentUser } from "@/lib/auth-server";
import {
  formatDateTime,
  formatPrice,
} from "@/lib/format";
import { getOrder } from "@/lib/order-server";
import type {
  OrderStatus,
} from "@/lib/order-types";


export const dynamic = "force-dynamic";

type RawSearchParams = Record<
  string,
  string | string[] | undefined
>;

interface OrderPageProps {
  params: Promise<{
    orderId: string;
  }>;

  searchParams: Promise<RawSearchParams>;
}


function getFirstValue(
  value: string | string[] | undefined,
): string | undefined {
  return Array.isArray(value)
    ? value[0]
    : value;
}


function statusLabel(
  value: string,
): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) =>
      letter.toUpperCase(),
    );
}


function statusClass(
  status: OrderStatus,
): string {
  switch (status) {
    case "delivered":
      return "bg-emerald-100 text-emerald-700";

    case "cancelled":
      return "bg-red-100 text-red-700";

    case "shipped":
      return "bg-blue-100 text-blue-700";

    case "processing":
    case "confirmed":
      return "bg-amber-100 text-amber-800";

    default:
      return "bg-slate-100 text-slate-700";
  }
}


export default async function OrderPage({
  params,
  searchParams,
}: OrderPageProps) {
  const currentUser = await getCurrentUser();

  if (!currentUser) {
    redirect("/login?next=/orders");
  }

  const [{ orderId }, queryParams] =
    await Promise.all([
      params,
      searchParams,
    ]);

  const result = await getOrder(orderId);

  if (result.status === "not_found") {
    notFound();
  }

  const message = getFirstValue(
    queryParams.message,
  );

  if (result.status === "unavailable") {
    return (
      <main className="min-h-screen bg-slate-50 text-slate-950">
        <StoreHeader />

        <section className="mx-auto max-w-4xl px-6 py-12">
          <div className="rounded-2xl border border-red-200 bg-white p-8">
            <h1 className="text-2xl font-bold">
              Order unavailable
            </h1>

            <p className="mt-3 text-slate-600">
              The order service could not be
              reached.
            </p>

            <Link
              href="/orders"
              className="mt-6 inline-block font-semibold underline"
            >
              Return to orders
            </Link>
          </div>
        </section>
      </main>
    );
  }

  const { order } = result;

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <StoreHeader />

      <section className="mx-auto max-w-7xl px-6 py-12">
        <Link
          href="/orders"
          className="text-sm font-semibold text-slate-600 hover:text-slate-950"
        >
          ← Back to orders
        </Link>

        {message ? (
          <div className="mt-8 rounded-xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-emerald-700">
            {message}
          </div>
        ) : null}

        <div className="mt-8 flex flex-wrap items-start justify-between gap-6">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
              Order confirmation
            </p>

            <h1 className="mt-2 text-3xl font-bold tracking-tight">
              {order.order_number}
            </h1>

            <p className="mt-3 text-sm text-slate-500">
              Placed{" "}
              {formatDateTime(order.created_at)}
            </p>
          </div>

          <span
            className={`rounded-full px-5 py-2 text-sm font-semibold ${statusClass(
              order.status,
            )}`}
          >
            {statusLabel(order.status)}
          </span>
        </div>

        <div className="mt-10 grid gap-8 lg:grid-cols-[1fr_380px]">
          <section className="space-y-8">
            <div className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
              <h2 className="text-2xl font-bold">
                Products
              </h2>

              <div className="mt-6 divide-y divide-slate-200">
                {order.items.map((item) => (
                  <article
                    key={item.id}
                    className="flex flex-wrap items-start justify-between gap-5 py-5 first:pt-0 last:pb-0"
                  >
                    <div>
                      {item.product_id ? (
                        <Link
                          href={`/products/${item.product_id}`}
                          className="font-bold hover:underline"
                        >
                          {item.product_name}
                        </Link>
                      ) : (
                        <p className="font-bold">
                          {item.product_name}
                        </p>
                      )}

                      <p className="mt-1 text-sm text-slate-500">
                        {item.product_brand}
                      </p>

                      <p className="mt-2 text-sm text-slate-600">
                        {formatPrice(
                          item.unit_price,
                        )}{" "}
                        × {item.quantity}
                      </p>
                    </div>

                    <p className="font-bold">
                      {formatPrice(
                        item.line_total,
                      )}
                    </p>
                  </article>
                ))}
              </div>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
              <h2 className="text-2xl font-bold">
                Order status
              </h2>

              <div className="mt-6 space-y-5">
                {order.status_history.map(
                  (history) => (
                    <div
                      key={history.id}
                      className="relative border-l-2 border-slate-200 pl-6"
                    >
                      <span className="absolute -left-[7px] top-1 h-3 w-3 rounded-full bg-slate-950" />

                      <p className="font-semibold">
                        {statusLabel(
                          history.status,
                        )}
                      </p>

                      <p className="mt-1 text-sm text-slate-500">
                        {formatDateTime(
                          history.created_at,
                        )}
                      </p>

                      {history.note ? (
                        <p className="mt-2 text-sm text-slate-600">
                          {history.note}
                        </p>
                      ) : null}
                    </div>
                  ),
                )}
              </div>
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
              <h2 className="text-xl font-bold">
                Payment summary
              </h2>

              <div className="mt-6 space-y-4 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-600">
                    Subtotal
                  </span>

                  <span className="font-semibold">
                    {formatPrice(
                      order.subtotal,
                    )}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-slate-600">
                    Shipping
                  </span>

                  <span className="font-semibold">
                    {formatPrice(
                      order.shipping_amount,
                    )}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-slate-600">
                    Tax
                  </span>

                  <span className="font-semibold">
                    {formatPrice(
                      order.tax_amount,
                    )}
                  </span>
                </div>

                <div className="flex justify-between border-t border-slate-200 pt-4 text-lg">
                  <span className="font-semibold">
                    Total
                  </span>

                  <span className="font-bold">
                    {formatPrice(
                      order.total_amount,
                    )}
                  </span>
                </div>
              </div>

              <div className="mt-6 rounded-xl bg-slate-50 px-4 py-3 text-sm">
                Payment status:{" "}
                <span className="font-semibold">
                  {statusLabel(
                    order.payment_status,
                  )}
                </span>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
              <h2 className="text-xl font-bold">
                Shipping address
              </h2>

              <address className="mt-5 text-sm not-italic leading-6 text-slate-600">
                <strong className="text-slate-950">
                  {
                    order.shipping_address
                      .full_name
                  }
                </strong>
                <br />

                {
                  order.shipping_address
                    .phone
                }
                <br />
                <br />

                {
                  order.shipping_address
                    .address_line_1
                }
                <br />

                {order.shipping_address
                  .address_line_2 ? (
                  <>
                    {
                      order.shipping_address
                        .address_line_2
                    }
                    <br />
                  </>
                ) : null}

                {
                  order.shipping_address.city
                }
                ,{" "}
                {
                  order.shipping_address.state
                }{" "}
                {
                  order.shipping_address
                    .postal_code
                }
                <br />

                {
                  order.shipping_address
                    .country_code
                }
              </address>
            </div>

            {order.customer_note ? (
              <div className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
                <h2 className="text-xl font-bold">
                  Delivery note
                </h2>

                <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-slate-600">
                  {order.customer_note}
                </p>
              </div>
            ) : null}
          </aside>
        </div>
      </section>
    </main>
  );
}
