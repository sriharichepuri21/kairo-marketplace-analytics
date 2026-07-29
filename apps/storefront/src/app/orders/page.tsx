import Link from "next/link";
import { redirect } from "next/navigation";

import { StoreHeader } from "@/components/store-header";
import { getCurrentUser } from "@/lib/auth-server";
import {
  formatDateTime,
  formatPrice,
} from "@/lib/format";
import { getOrders } from "@/lib/order-server";
import type {
  Order,
  OrderStatus,
} from "@/lib/order-types";


export const dynamic = "force-dynamic";

type RawSearchParams = Record<
  string,
  string | string[] | undefined
>;

interface OrdersPageProps {
  searchParams: Promise<RawSearchParams>;
}


function getFirstValue(
  value: string | string[] | undefined,
): string | undefined {
  return Array.isArray(value)
    ? value[0]
    : value;
}


function orderItemCount(
  order: Order,
): number {
  return order.items.reduce(
    (total, item) =>
      total + item.quantity,
    0,
  );
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


export default async function OrdersPage({
  searchParams,
}: OrdersPageProps) {
  const currentUser = await getCurrentUser();

  if (!currentUser) {
    redirect("/login?next=/orders");
  }

  const [orders, params] =
    await Promise.all([
      getOrders(),
      searchParams,
    ]);

  const message = getFirstValue(
    params.message,
  );

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <StoreHeader />

      <section className="mx-auto max-w-7xl px-6 py-12">
        <div className="flex flex-wrap items-end justify-between gap-5">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
              Customer account
            </p>

            <h1 className="mt-2 text-4xl font-bold tracking-tight">
              Your orders
            </h1>

            <p className="mt-3 text-slate-600">
              Review your purchases and delivery
              status.
            </p>
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

        {!orders ? (
          <div className="mt-10 rounded-2xl border border-red-200 bg-white p-8">
            <h2 className="text-xl font-bold">
              Orders unavailable
            </h2>

            <p className="mt-3 text-slate-600">
              The order service could not be
              reached.
            </p>
          </div>
        ) : orders.length === 0 ? (
          <div className="mt-10 rounded-3xl border border-slate-200 bg-white p-12 text-center shadow-sm">
            <h2 className="text-2xl font-bold">
              No orders yet
            </h2>

            <p className="mt-3 text-slate-600">
              Products you purchase will appear
              here.
            </p>

            <Link
              href="/#catalogue"
              className="mt-7 inline-block rounded-xl bg-slate-950 px-6 py-3 font-semibold text-white"
            >
              Browse products
            </Link>
          </div>
        ) : (
          <div className="mt-10 space-y-5">
            {orders.map((order) => (
              <article
                key={order.id}
                className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
              >
                <div className="flex flex-wrap items-start justify-between gap-5">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                      Order
                    </p>

                    <Link
                      href={`/orders/${order.id}`}
                      className="mt-1 block text-xl font-bold hover:underline"
                    >
                      {order.order_number}
                    </Link>

                    <p className="mt-2 text-sm text-slate-500">
                      {formatDateTime(
                        order.created_at,
                      )}
                    </p>
                  </div>

                  <span
                    className={`rounded-full px-4 py-2 text-xs font-semibold ${statusClass(
                      order.status,
                    )}`}
                  >
                    {statusLabel(order.status)}
                  </span>
                </div>

                <div className="mt-6 grid gap-5 border-t border-slate-200 pt-5 sm:grid-cols-3">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">
                      Items
                    </p>

                    <p className="mt-1 font-semibold">
                      {orderItemCount(order)}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">
                      Payment
                    </p>

                    <p className="mt-1 font-semibold">
                      {statusLabel(
                        order.payment_status,
                      )}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">
                      Total
                    </p>

                    <p className="mt-1 font-bold">
                      {formatPrice(
                        order.total_amount,
                      )}
                    </p>
                  </div>
                </div>

                <Link
                  href={`/orders/${order.id}`}
                  className="mt-6 inline-block text-sm font-semibold underline-offset-4 hover:underline"
                >
                  View order details →
                </Link>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
