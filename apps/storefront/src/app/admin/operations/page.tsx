import Link from "next/link";
import { redirect } from "next/navigation";

import {
  getCurrentUser,
} from "@/lib/auth-server";
import {
  getOperationsOrderStatuses,
  getOperationsRevenueTrend,
  getOperationsSummary,
} from "@/lib/operations-server";
import type {
  OperationsOrderStatuses,
  OperationsRevenueTrend,
  OperationsRevenueTrendPoint,
  OperationsSummary,
} from "@/lib/operations-types";
import { StoreHeader } from "@/components/store-header";


export const dynamic = "force-dynamic";
export const revalidate = 0;
export const fetchCache = "force-no-store";

type RawSearchParams = Record<
  string,
  string | string[] | undefined
>;

interface OperationsPageProps {
  searchParams: Promise<RawSearchParams>;
}

interface DashboardData {
  summary: OperationsSummary;
  revenueTrend: OperationsRevenueTrend;
  orderStatuses: OperationsOrderStatuses;
}

const allowedPeriods = new Set([
  30,
  90,
  180,
  365,
]);


function getFirstValue(
  value: string | string[] | undefined,
): string | undefined {
  return Array.isArray(value)
    ? value[0]
    : value;
}


function getDays(
  value: string | undefined,
): number {
  const parsed = Number(value);

  if (
    !Number.isInteger(parsed)
    || !allowedPeriods.has(parsed)
  ) {
    return 90;
  }

  return parsed;
}


async function loadDashboard(
  days: number,
): Promise<DashboardData | null> {
  try {
    const [
      summary,
      revenueTrend,
      orderStatuses,
    ] = await Promise.all([
      getOperationsSummary(days),
      getOperationsRevenueTrend(days),
      getOperationsOrderStatuses(days),
    ]);

    if (
      !summary
      || !revenueTrend
      || !orderStatuses
    ) {
      return null;
    }

    return {
      summary,
      revenueTrend,
      orderStatuses,
    };
  } catch (error) {
    console.error(
      "Failed to load operations dashboard:",
      error,
    );

    return null;
  }
}


function formatNumber(
  value: number,
): string {
  return new Intl.NumberFormat(
    "en-IN",
  ).format(value);
}


function formatCurrency(
  value: string | number,
  currencyCode: string,
): string {
  return new Intl.NumberFormat(
    "en-IN",
    {
      style: "currency",
      currency: currencyCode,
      maximumFractionDigits: 2,
    },
  ).format(Number(value));
}


function formatPercent(
  value: number,
): string {
  return new Intl.NumberFormat(
    "en-IN",
    {
      style: "percent",
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    },
  ).format(value);
}


function formatDate(
  value: string,
): string {
  return new Intl.DateTimeFormat(
    "en-IN",
    {
      dateStyle: "medium",
      timeZone: "UTC",
    },
  ).format(
    new Date(`${value}T00:00:00Z`),
  );
}


function statusLabel(
  value: string,
): string {
  return value
    .split("_")
    .map(
      (part) =>
        part.charAt(0).toUpperCase()
        + part.slice(1),
    )
    .join(" ");
}


function groupTrendByCurrency(
  items: OperationsRevenueTrendPoint[],
): Map<
  string,
  OperationsRevenueTrendPoint[]
> {
  const groups = new Map<
    string,
    OperationsRevenueTrendPoint[]
  >();

  for (const item of items) {
    const currencyItems =
      groups.get(item.currency_code)
      ?? [];

    currencyItems.push(item);

    groups.set(
      item.currency_code,
      currencyItems,
    );
  }

  return groups;
}


function MetricCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-sm font-medium text-slate-500">
        {label}
      </p>

      <p className="mt-3 text-3xl font-bold tracking-tight text-slate-950">
        {value}
      </p>

      <p className="mt-2 text-sm text-slate-500">
        {detail}
      </p>
    </article>
  );
}


interface RevenueChartBar {
  startDate: string;
  endDate: string;
  eligibleOrders: number;
  grossSales: number;
}


function buildRevenueChartBars(
  items: OperationsRevenueTrendPoint[],
  maximumBars = 30,
): RevenueChartBar[] {
  if (items.length === 0) {
    return [];
  }

  const bucketSize = Math.max(
    1,
    Math.ceil(
      items.length / maximumBars,
    ),
  );

  const bars: RevenueChartBar[] = [];

  for (
    let index = 0;
    index < items.length;
    index += bucketSize
  ) {
    const bucket = items.slice(
      index,
      index + bucketSize,
    );

    const firstItem = bucket[0];
    const lastItem =
      bucket[bucket.length - 1];

    if (!firstItem || !lastItem) {
      continue;
    }

    bars.push({
      startDate: firstItem.order_date,
      endDate: lastItem.order_date,
      eligibleOrders: bucket.reduce(
        (total, item) =>
          total + item.eligible_orders,
        0,
      ),
      grossSales: bucket.reduce(
        (total, item) =>
          total
          + Number(item.gross_sales),
        0,
      ),
    });
  }

  return bars;
}


function RevenueChart({
  currencyCode,
  items,
}: {
  currencyCode: string;
  items: OperationsRevenueTrendPoint[];
}) {
  const chartBars =
    buildRevenueChartBars(items);

  const maximumRevenue = Math.max(
    ...chartBars.map(
      (bar) => bar.grossSales,
    ),
    1,
  );

  const totalRevenue = items.reduce(
    (total, item) =>
      total + Number(item.gross_sales),
    0,
  );

  const totalOrders = items.reduce(
    (total, item) =>
      total + item.eligible_orders,
    0,
  );

  const firstItem = items[0];
  const lastItem =
    items[items.length - 1];

  const chartDescription =
    items.length > chartBars.length
      ? (
          `${items.length} active days grouped `
          + `into ${chartBars.length} bars`
        )
      : `${items.length} active days in period`;

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
            {currencyCode} revenue
          </p>

          <p className="mt-2 text-2xl font-bold">
            {formatCurrency(
              totalRevenue,
              currencyCode,
            )}
          </p>

          <p className="mt-1 text-sm text-slate-500">
            {formatNumber(totalOrders)} eligible
            orders in the displayed period
          </p>
        </div>

        <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-700">
          {chartDescription}
        </span>
      </div>

      {chartBars.length > 0 ? (
        <>
          <div className="mt-8 flex h-56 items-end gap-1 overflow-hidden border-b border-slate-200">
            {chartBars.map((bar) => {
              const percentage = Math.max(
                (
                  bar.grossSales
                  / maximumRevenue
                ) * 100,
                2,
              );

              const dateLabel =
                bar.startDate === bar.endDate
                  ? formatDate(
                      bar.startDate,
                    )
                  : (
                      `${formatDate(
                        bar.startDate,
                      )} – ${formatDate(
                        bar.endDate,
                      )}`
                    );

              return (
                <div
                  key={
                    bar.startDate
                    + bar.endDate
                    + currencyCode
                  }
                  className="group relative flex h-full min-w-[3px] flex-1 items-end"
                  title={
                    `${dateLabel}: ${formatCurrency(
                      bar.grossSales,
                      currencyCode,
                    )} from ${formatNumber(
                      bar.eligibleOrders,
                    )} orders`
                  }
                >
                  <div
                    className="w-full rounded-t bg-slate-900 transition group-hover:bg-slate-600"
                    style={{
                      height: `${percentage}%`,
                    }}
                  />
                </div>
              );
            })}
          </div>

          {firstItem && lastItem ? (
            <div className="mt-3 flex justify-between text-xs text-slate-500">
              <span>
                {formatDate(
                  firstItem.order_date,
                )}
              </span>

              <span>
                {formatDate(
                  lastItem.order_date,
                )}
              </span>
            </div>
          ) : null}
        </>
      ) : (
        <div className="mt-8 flex h-56 items-center justify-center rounded-xl bg-slate-50 text-sm text-slate-500">
          No eligible revenue in this period
        </div>
      )}
    </article>
  );
}


function DashboardUnavailable() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <StoreHeader />

      <section className="mx-auto max-w-7xl px-6 py-16">
        <div className="rounded-3xl border border-amber-200 bg-white p-10 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-amber-700">
            Marketplace operations
          </p>

          <h1 className="mt-3 text-3xl font-bold">
            Operations analytics are unavailable
          </h1>

          <p className="mt-4 max-w-2xl leading-7 text-slate-600">
            Confirm the API is running and the
            operational marketplace data has been
            imported.
          </p>
        </div>
      </section>
    </main>
  );
}


export default async function OperationsPage({
  searchParams,
}: OperationsPageProps) {
  const currentUser =
    await getCurrentUser();

  if (!currentUser) {
    redirect(
      "/login?next=/admin/operations",
    );
  }

  if (currentUser.role !== "admin") {
    redirect("/");
  }

  const params = await searchParams;

  const days = getDays(
    getFirstValue(params.days),
  );

  const data = await loadDashboard(
    days,
  );

  if (!data) {
    return <DashboardUnavailable />;
  }

  const {
    summary,
    revenueTrend,
    orderStatuses,
  } = data;

  const deliveredRate =
    summary.total_orders > 0
      ? (
          summary.delivered_orders
          / summary.total_orders
        )
      : 0;

  const cancelledRate =
    summary.total_orders > 0
      ? (
          summary.cancelled_orders
          / summary.total_orders
        )
      : 0;

  const trendGroups =
    groupTrendByCurrency(
      revenueTrend.items,
    );

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <StoreHeader />

      <section className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-6 py-10">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
                Marketplace intelligence
              </p>

              <h1 className="mt-3 text-4xl font-bold tracking-tight">
                Operations dashboard
              </h1>

              <p className="mt-3 max-w-3xl leading-7 text-slate-600">
                Monitor order volume, customer
                activity, revenue by currency, and
                fulfilment performance from the
                operational marketplace database.
              </p>

              {summary.snapshot_date ? (
                <p className="mt-3 text-sm text-slate-500">
                  Latest operational date{" "}
                  <strong>
                    {formatDate(
                      summary.snapshot_date,
                    )}
                  </strong>
                </p>
              ) : null}
            </div>

            <Link
              href="/admin/churn"
              className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold transition hover:border-slate-950"
            >
              View churn dashboard
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-10">
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-5">
          <MetricCard
            label="Total orders"
            value={formatNumber(
              summary.total_orders,
            )}
            detail="All operational orders"
          />

          <MetricCard
            label="Eligible orders"
            value={formatNumber(
              summary.eligible_orders,
            )}
            detail="Paid and not cancelled"
          />

          <MetricCard
            label="Active customers"
            value={formatNumber(
              summary.active_customers,
            )}
            detail="Customers with eligible orders"
          />

          <MetricCard
            label="Delivered orders"
            value={formatNumber(
              summary.delivered_orders,
            )}
            detail={`${formatPercent(
              deliveredRate,
            )} of all orders`}
          />

          <MetricCard
            label="Cancelled orders"
            value={formatNumber(
              summary.cancelled_orders,
            )}
            detail={`${formatPercent(
              cancelledRate,
            )} of all orders`}
          />
        </div>

        <div className="mt-8">
          <div className="flex flex-wrap items-end justify-between gap-5">
            <div>
              <h2 className="text-2xl font-bold">
                Revenue by currency
              </h2>

              <p className="mt-2 text-slate-600">
                Selected-period totals are kept
                separate by transaction currency.
              </p>
            </div>

            <form
              method="get"
              className="flex items-end gap-3"
            >
              <label>
                <span className="mb-2 block text-sm font-medium text-slate-700">
                  Analysis period
                </span>

                <select
                  name="days"
                  defaultValue={String(days)}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-3"
                >
                  <option value="30">
                    Last 30 days
                  </option>

                  <option value="90">
                    Last 90 days
                  </option>

                  <option value="180">
                    Last 180 days
                  </option>

                  <option value="365">
                    Last 365 days
                  </option>
                </select>
              </label>

              <button
                type="submit"
                className="rounded-xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
              >
                Apply
              </button>
            </form>
          </div>

          <div className="mt-6 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {summary.revenue_by_currency.map(
              (currency) => (
                <article
                  key={currency.currency_code}
                  className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
                >
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
                      {currency.currency_code}
                    </p>

                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold">
                      {
                        currency.eligible_orders
                      }{" "}
                      orders
                    </span>
                  </div>

                  <p className="mt-5 text-3xl font-bold">
                    {formatCurrency(
                      currency.gross_sales,
                      currency.currency_code,
                    )}
                  </p>

                  <p className="mt-3 text-sm text-slate-500">
                    Average order value{" "}
                    <strong className="text-slate-700">
                      {formatCurrency(
                        currency.average_order_value,
                        currency.currency_code,
                      )}
                    </strong>
                  </p>
                </article>
              ),
            )}
          </div>
        </div>

        <div className="mt-10">
          <h2 className="text-2xl font-bold">
            Revenue trend
          </h2>

          <p className="mt-2 text-slate-600">
            Daily eligible-order revenue, separated
            by transaction currency.
          </p>

          <div className="mt-6 grid gap-6 xl:grid-cols-3">
            {Array.from(
              trendGroups.entries(),
            ).map(
              ([
                currencyCode,
                items,
              ]) => (
                <RevenueChart
                  key={currencyCode}
                  currencyCode={
                    currencyCode
                  }
                  items={items}
                />
              ),
            )}
          </div>
        </div>

        <div className="mt-10 rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div>
              <h2 className="text-2xl font-bold">
                Order-status distribution
              </h2>

              <p className="mt-2 text-slate-600">
                {formatNumber(
                  orderStatuses.total_orders,
                )}{" "}
                orders in the selected period
              </p>
            </div>

            {orderStatuses.start_date
            && orderStatuses.end_date ? (
              <p className="text-sm text-slate-500">
                {formatDate(
                  orderStatuses.start_date,
                )}{" "}
                –{" "}
                {formatDate(
                  orderStatuses.end_date,
                )}
              </p>
            ) : null}
          </div>

          <div className="mt-8 space-y-6">
            {orderStatuses.items.map(
              (item) => {
                const percentage =
                  item.order_percentage * 100;

                return (
                  <div key={item.status}>
                    <div className="mb-2 flex items-center justify-between gap-5">
                      <p className="font-semibold">
                        {statusLabel(
                          item.status,
                        )}
                      </p>

                      <p className="text-sm text-slate-500">
                        {formatNumber(
                          item.order_count,
                        )}{" "}
                        ·{" "}
                        {formatPercent(
                          item.order_percentage,
                        )}
                      </p>
                    </div>

                    <div className="h-3 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full rounded-full bg-slate-900"
                        style={{
                          width: `${
                            Math.max(
                              percentage,
                              0.5,
                            )
                          }%`,
                        }}
                      />
                    </div>
                  </div>
                );
              },
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
