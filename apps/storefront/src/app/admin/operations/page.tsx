import Link from "next/link";
import { redirect } from "next/navigation";

import {
  getCurrentUser,
} from "@/lib/auth-server";
import {
  getOperationsCategoryPerformance,
  getOperationsConversionFunnel,
  getOperationsInventoryAlerts,
  getOperationsOrderStatuses,
  getOperationsRevenueTrend,
  getOperationsSummary,
} from "@/lib/operations-server";
import type {
  OperationsCategoryPerformance,
  OperationsConversionFunnel,
  OperationsInventoryAlerts,
  OperationsInventoryStatus,
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
  conversionFunnel:
    OperationsConversionFunnel;
  categoryPerformance:
    OperationsCategoryPerformance;
  inventoryAlerts:
    OperationsInventoryAlerts;
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



function getInventoryPage(
  value: string | undefined,
): number {
  const parsed = Number(value);

  if (
    !Number.isSafeInteger(parsed)
    || parsed < 1
  ) {
    return 1;
  }

  return parsed;
}


async function loadDashboard(
  days: number,
  inventoryPage: number,
): Promise<DashboardData | null> {
  try {
    const [
      summary,
      revenueTrend,
      orderStatuses,
      conversionFunnel,
      categoryPerformance,
      inventoryAlerts,
    ] = await Promise.all([
      getOperationsSummary(days),
      getOperationsRevenueTrend(days),
      getOperationsOrderStatuses(days),
      getOperationsConversionFunnel(days),
      getOperationsCategoryPerformance(days),
      getOperationsInventoryAlerts({
        threshold: 10,
        page: inventoryPage,
        pageSize: 10,
      }),
    ]);

    if (
      !summary
      || !revenueTrend
      || !orderStatuses
      || !conversionFunnel
      || !categoryPerformance
      || !inventoryAlerts
    ) {
      return null;
    }

    return {
      summary,
      revenueTrend,
      orderStatuses,
      conversionFunnel,
      categoryPerformance,
      inventoryAlerts,
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




function createInventoryPageHref(
  days: number,
  page: number,
): string {
  const params = new URLSearchParams({
    days: String(days),
    inventory_page: String(page),
  });

  return (
    `/admin/operations?${params.toString()}`
    + "#inventory-health"
  );
}


function inventoryStatusClasses(
  status: OperationsInventoryStatus,
): string {
  switch (status) {
    case "untracked":
      return (
        "bg-slate-100 text-slate-700"
      );

    case "out_of_stock":
      return (
        "bg-red-100 text-red-700"
      );

    case "critical_stock":
      return (
        "bg-amber-100 text-amber-800"
      );

    case "low_stock":
      return (
        "bg-blue-100 text-blue-700"
      );
  }
}




function ConversionFunnelSection({
  data,
}: {
  data: OperationsConversionFunnel;
}) {
  const stages = [
    {
      key: "product-view",
      label: "Product views",
      sessions: data.product_view_sessions,
      conversionRate: null,
      dropoffs: data.view_dropoffs,
      nextStage: "add to cart",
    },
    {
      key: "add-to-cart",
      label: "Added to cart",
      sessions: data.add_to_cart_sessions,
      conversionRate:
        data.view_to_cart_rate,
      dropoffs: data.cart_dropoffs,
      nextStage: "checkout",
    },
    {
      key: "checkout-started",
      label: "Checkout started",
      sessions:
        data.checkout_started_sessions,
      conversionRate:
        data.cart_to_checkout_rate,
      dropoffs:
        data.checkout_dropoffs,
      nextStage: "order placement",
    },
    {
      key: "order-placed",
      label: "Orders placed",
      sessions: data.order_placed_sessions,
      conversionRate:
        data.checkout_to_order_rate,
      dropoffs: null,
      nextStage: null,
    },
  ];

  const funnelEntry =
    data.product_view_sessions;

  return (
    <section
      id="conversion-funnel"
      className="mt-10 rounded-3xl border border-slate-200 bg-white p-7 shadow-sm"
    >
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
            Customer journey
          </p>

          <h2 className="mt-2 text-2xl font-bold">
            Conversion funnel
          </h2>

          <p className="mt-2 max-w-3xl leading-7 text-slate-600">
            Session-level progression from product
            discovery through completed order
            placement.
          </p>
        </div>

        <div className="rounded-2xl bg-slate-950 px-6 py-4 text-white">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">
            Overall conversion
          </p>

          <p className="mt-2 text-3xl font-bold">
            {formatPercent(
              data.overall_conversion_rate,
            )}
          </p>
        </div>
      </div>

      {data.start_date
      && data.end_date ? (
        <p className="mt-4 text-sm text-slate-500">
          {formatDate(data.start_date)}
          {" – "}
          {formatDate(data.end_date)}
          {" · "}
          {formatNumber(
            data.total_sessions,
          )}{" "}
          funnel sessions
        </p>
      ) : null}

      <div className="mt-8 grid gap-8 xl:grid-cols-[minmax(0,1.7fr)_minmax(280px,0.6fr)]">
        <div className="space-y-6">
          {stages.map((stage) => {
            const width = funnelEntry > 0
              ? Math.max(
                  (
                    stage.sessions
                    / funnelEntry
                  ) * 100,
                  4,
                )
              : 0;

            return (
              <article key={stage.key}>
                <div className="flex flex-wrap items-end justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-slate-950">
                      {stage.label}
                    </h3>

                    <p className="mt-1 text-sm text-slate-500">
                      {stage.conversionRate
                        === null
                        ? "Funnel entry"
                        : (
                            `${formatPercent(
                              stage.conversionRate,
                            )} from the previous stage`
                          )}
                    </p>
                  </div>

                  <p className="text-2xl font-bold">
                    {formatNumber(
                      stage.sessions,
                    )}
                  </p>
                </div>

                <div className="mt-3 h-5 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-slate-950"
                    style={{
                      width: `${width}%`,
                    }}
                  />
                </div>

                {stage.dropoffs !== null
                && stage.nextStage ? (
                  <p className="mt-2 text-sm text-slate-500">
                    {formatNumber(
                      stage.dropoffs,
                    )}{" "}
                    sessions dropped before{" "}
                    {stage.nextStage}
                  </p>
                ) : (
                  <p className="mt-2 text-sm font-medium text-emerald-700">
                    Completed marketplace orders
                  </p>
                )}
              </article>
            );
          })}
        </div>

        <aside className="grid content-start gap-4 sm:grid-cols-2 xl:grid-cols-1">
          <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
            <p className="text-sm font-medium text-slate-500">
              View → cart
            </p>

            <p className="mt-2 text-2xl font-bold">
              {formatPercent(
                data.view_to_cart_rate,
              )}
            </p>

            <p className="mt-2 text-sm text-slate-500">
              {formatNumber(
                data.view_dropoffs,
              )}{" "}
              view-stage drop-offs
            </p>
          </article>

          <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
            <p className="text-sm font-medium text-slate-500">
              Cart → checkout
            </p>

            <p className="mt-2 text-2xl font-bold">
              {formatPercent(
                data.cart_to_checkout_rate,
              )}
            </p>

            <p className="mt-2 text-sm text-slate-500">
              {formatNumber(
                data.cart_dropoffs,
              )}{" "}
              cart abandonments
            </p>
          </article>

          <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
            <p className="text-sm font-medium text-slate-500">
              Checkout → order
            </p>

            <p className="mt-2 text-2xl font-bold">
              {formatPercent(
                data.checkout_to_order_rate,
              )}
            </p>

            <p className="mt-2 text-sm text-slate-500">
              {formatNumber(
                data.checkout_dropoffs,
              )}{" "}
              checkout abandonments
            </p>
          </article>

          <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
            <p className="text-sm font-medium text-slate-500">
              Completed orders
            </p>

            <p className="mt-2 text-2xl font-bold">
              {formatNumber(
                data.order_placed_sessions,
              )}
            </p>

            <p className="mt-2 text-sm text-slate-500">
              Distinct converted sessions
            </p>
          </article>
        </aside>
      </div>
    </section>
  );
}


function CategoryPerformanceSection({
  data,
}: {
  data: OperationsCategoryPerformance;
}) {
  return (
    <section className="mt-10">
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div>
          <h2 className="text-2xl font-bold">
            Category performance
          </h2>

          <p className="mt-2 text-slate-600">
            Eligible-order sales, products, units,
            and revenue contribution by category.
          </p>
        </div>

        {data.start_date
        && data.end_date ? (
          <p className="text-sm text-slate-500">
            {formatDate(data.start_date)}
            {" – "}
            {formatDate(data.end_date)}
          </p>
        ) : null}
      </div>

      {data.items.length > 0 ? (
        <div className="mt-6 grid gap-5 lg:grid-cols-2">
          {data.items.map(
            (category) => (
              <article
                key={category.category_id}
                className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
              >
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h3 className="text-xl font-bold">
                      {category.category_name}
                    </h3>

                    <p className="mt-2 text-sm text-slate-500">
                      {formatNumber(
                        category.products_sold,
                      )}{" "}
                      products sold
                    </p>
                  </div>

                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                    {formatNumber(
                      category.units_sold,
                    )}{" "}
                    units
                  </span>
                </div>

                <div className="mt-5 grid grid-cols-2 gap-4 rounded-xl bg-slate-50 p-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Eligible orders
                    </p>

                    <p className="mt-1 text-lg font-bold">
                      {formatNumber(
                        category.eligible_orders,
                      )}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Units sold
                    </p>

                    <p className="mt-1 text-lg font-bold">
                      {formatNumber(
                        category.units_sold,
                      )}
                    </p>
                  </div>
                </div>

                <div className="mt-5 divide-y divide-slate-100">
                  {category.revenue_by_currency.map(
                    (currency) => (
                      <div
                        key={
                          category.category_id
                          + currency.currency_code
                        }
                        className="flex flex-wrap items-center justify-between gap-4 py-4 first:pt-0 last:pb-0"
                      >
                        <div>
                          <p className="text-sm font-bold">
                            {
                              currency.currency_code
                            }
                          </p>

                          <p className="mt-1 text-xs text-slate-500">
                            {formatNumber(
                              currency.units_sold,
                            )}{" "}
                            units ·{" "}
                            {formatPercent(
                              currency.revenue_share,
                            )}{" "}
                            of currency revenue
                          </p>
                        </div>

                        <div className="text-right">
                          <p className="font-bold">
                            {formatCurrency(
                              currency.gross_sales,
                              currency.currency_code,
                            )}
                          </p>

                          <p className="mt-1 text-xs text-slate-500">
                            {formatCurrency(
                              currency.average_unit_revenue,
                              currency.currency_code,
                            )}{" "}
                            per unit
                          </p>
                        </div>
                      </div>
                    ),
                  )}
                </div>
              </article>
            ),
          )}
        </div>
      ) : (
        <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-10 text-center text-slate-500 shadow-sm">
          No eligible category sales were found
          for this period.
        </div>
      )}
    </section>
  );
}


function InventoryHealthSection({
  data,
  days,
}: {
  data: OperationsInventoryAlerts;
  days: number;
}) {
  return (
    <section
      id="inventory-health"
      className="mt-10 scroll-mt-8"
    >
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div>
          <h2 className="text-2xl font-bold">
            Inventory health
          </h2>

          <p className="mt-2 text-slate-600">
            Current stock snapshot. Products with
            available quantity at or below{" "}
            {data.low_stock_threshold} appear in
            the alert queue.
          </p>
        </div>

        <span className="rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white">
          {formatNumber(
            data.total_items,
          )}{" "}
          active alerts
        </span>
      </div>

      <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <MetricCard
          label="Total products"
          value={formatNumber(
            data.total_products,
          )}
          detail="Marketplace catalogue"
        />

        <MetricCard
          label="Critical stock"
          value={formatNumber(
            data.critical_stock_products,
          )}
          detail="Available quantity 1–5"
        />

        <MetricCard
          label="Low stock"
          value={formatNumber(
            data.low_stock_products,
          )}
          detail={
            `Available quantity 6–${
              data.low_stock_threshold
            }`
          }
        />

        <MetricCard
          label="Healthy stock"
          value={formatNumber(
            data.healthy_stock_products,
          )}
          detail={
            `Above ${
              data.low_stock_threshold
            } available`
          }
        />

        <MetricCard
          label="Out of stock"
          value={formatNumber(
            data.out_of_stock_products,
          )}
          detail="Zero available"
        />

        <MetricCard
          label="Untracked"
          value={formatNumber(
            data.untracked_products,
          )}
          detail="No inventory record"
        />
      </div>

      <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 px-6 py-5">
          <div>
            <h3 className="text-lg font-bold">
              Inventory alert queue
            </h3>

            <p className="mt-1 text-sm text-slate-500">
              Critical products appear before
              low-stock products.
            </p>
          </div>

          <p className="text-sm font-medium text-slate-500">
            Page {data.page} of{" "}
            {Math.max(data.total_pages, 1)}
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-6 py-4">
                  Product
                </th>

                <th className="px-6 py-4">
                  Category
                </th>

                <th className="px-6 py-4">
                  Available
                </th>

                <th className="px-6 py-4">
                  Reserved
                </th>

                <th className="px-6 py-4">
                  Status
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-100">
              {data.items.map(
                (item) => (
                  <tr
                    key={item.product_id}
                    className="align-top"
                  >
                    <td className="px-6 py-4">
                      <p className="font-semibold text-slate-950">
                        {item.product_name}
                      </p>

                      <p className="mt-1 text-xs text-slate-500">
                        {item.brand}
                        {item.sku
                          ? ` · ${item.sku}`
                          : ""}
                      </p>
                    </td>

                    <td className="px-6 py-4 text-slate-600">
                      {item.category_name}
                    </td>

                    <td className="px-6 py-4 font-semibold">
                      {
                        item.available_quantity
                        ?? "—"
                      }
                    </td>

                    <td className="px-6 py-4 text-slate-600">
                      {
                        item.reserved_quantity
                        ?? "—"
                      }
                    </td>

                    <td className="px-6 py-4">
                      <span
                        className={
                          "inline-flex rounded-full "
                          + "px-3 py-1 text-xs "
                          + "font-semibold "
                          + inventoryStatusClasses(
                            item.inventory_status,
                          )
                        }
                      >
                        {statusLabel(
                          item.inventory_status,
                        )}
                      </span>
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>

        {data.items.length === 0 ? (
          <div className="px-6 py-12 text-center text-sm text-slate-500">
            No inventory alerts were found on
            this page.
          </div>
        ) : null}

        {data.total_pages > 1 ? (
          <nav className="flex items-center justify-center gap-4 border-t border-slate-200 px-6 py-5">
            {data.page > 1 ? (
              <Link
                href={createInventoryPageHref(
                  days,
                  data.page - 1,
                )}
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
              Page {data.page} of{" "}
              {data.total_pages}
            </span>

            {data.page
            < data.total_pages ? (
              <Link
                href={createInventoryPageHref(
                  days,
                  data.page + 1,
                )}
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
        ) : null}
      </div>
    </section>
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

  const inventoryPage =
    getInventoryPage(
      getFirstValue(
        params.inventory_page,
      ),
    );

  const data = await loadDashboard(
    days,
    inventoryPage,
  );

  if (!data) {
    return <DashboardUnavailable />;
  }

  const {
    summary,
    revenueTrend,
    orderStatuses,
    conversionFunnel,
    categoryPerformance,
    inventoryAlerts,
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

        <ConversionFunnelSection
          data={conversionFunnel}
        />

        <CategoryPerformanceSection
          data={categoryPerformance}
        />

        <InventoryHealthSection
          data={inventoryAlerts}
          days={days}
        />

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
