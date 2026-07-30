import Link from "next/link";
import { redirect } from "next/navigation";

import { StoreHeader } from "@/components/store-header";
import {
  getChurnCustomers,
  getChurnSummary,
} from "@/lib/churn-server";
import type {
  ChurnCustomerFilters,
  ChurnRiskSegment,
  CustomerChurnScorePage,
  CustomerChurnSummary,
} from "@/lib/churn-types";
import { formatPrice } from "@/lib/format";
import {
  getCurrentUser,
} from "@/lib/auth-server";


export const dynamic = "force-dynamic";

type RawSearchParams = Record<
  string,
  string | string[] | undefined
>;

interface AdminChurnPageProps {
  searchParams: Promise<RawSearchParams>;
}

interface DashboardData {
  summary: CustomerChurnSummary;
  customers: CustomerChurnScorePage;
}

const validRiskSegments =
  new Set<ChurnRiskSegment>([
    "high_risk",
    "medium_risk",
    "low_risk",
  ]);


function getFirstValue(
  value: string | string[] | undefined,
): string | undefined {
  return Array.isArray(value)
    ? value[0]
    : value;
}


function getPositiveInteger(
  value: string | undefined,
  fallback: number,
): number {
  const parsed = Number(value);

  if (
    !Number.isInteger(parsed) ||
    parsed < 1
  ) {
    return fallback;
  }

  return parsed;
}


function getRiskSegment(
  value: string | undefined,
): ChurnRiskSegment | undefined {
  if (
    value &&
    validRiskSegments.has(
      value as ChurnRiskSegment,
    )
  ) {
    return value as ChurnRiskSegment;
  }

  return undefined;
}


function getPredictedChurn(
  value: string | undefined,
): boolean | undefined {
  if (value === "true") {
    return true;
  }

  if (value === "false") {
    return false;
  }

  return undefined;
}


function getFilters(
  params: RawSearchParams,
): ChurnCustomerFilters {
  return {
    page: getPositiveInteger(
      getFirstValue(params.page),
      1,
    ),
    pageSize: 20,
    riskSegment: getRiskSegment(
      getFirstValue(
        params.risk_segment,
      ),
    ),
    predictedChurn: getPredictedChurn(
      getFirstValue(
        params.predicted_churn,
      ),
    ),
    search:
      getFirstValue(params.search)
        ?.trim() || undefined,
  };
}


async function loadDashboard(
  filters: ChurnCustomerFilters,
): Promise<DashboardData | null> {
  try {
    const [summary, customers] =
      await Promise.all([
        getChurnSummary(),
        getChurnCustomers(filters),
      ]);

    if (!summary || !customers) {
      return null;
    }

    return {
      summary,
      customers,
    };
  } catch (error) {
    console.error(
      "Failed to load churn dashboard:",
      error,
    );

    return null;
  }
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


function formatDateTime(
  value: string,
): string {
  return new Intl.DateTimeFormat(
    "en-IN",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(new Date(value));
}


function riskLabel(
  value: ChurnRiskSegment,
): string {
  const labels = {
    high_risk: "High risk",
    medium_risk: "Medium risk",
    low_risk: "Low risk",
  };

  return labels[value];
}


function riskClassName(
  value: ChurnRiskSegment,
): string {
  const styles = {
    high_risk:
      "bg-red-100 text-red-700",
    medium_risk:
      "bg-amber-100 text-amber-700",
    low_risk:
      "bg-emerald-100 text-emerald-700",
  };

  return styles[value];
}


function actionLabel(
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


function buildPageHref(
  filters: ChurnCustomerFilters,
  page: number,
): string {
  const params = new URLSearchParams();

  params.set("page", String(page));

  if (filters.riskSegment) {
    params.set(
      "risk_segment",
      filters.riskSegment,
    );
  }

  if (
    filters.predictedChurn !== undefined
  ) {
    params.set(
      "predicted_churn",
      String(filters.predictedChurn),
    );
  }

  if (filters.search) {
    params.set(
      "search",
      filters.search,
    );
  }

  return `/admin/churn?${params.toString()}`;
}


function MetricCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string | number;
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


function DashboardUnavailable() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <StoreHeader />

      <section className="mx-auto max-w-7xl px-6 py-16">
        <div className="rounded-3xl border border-amber-200 bg-white p-10 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-amber-700">
            Customer intelligence
          </p>

          <h1 className="mt-3 text-3xl font-bold">
            Churn scores are unavailable
          </h1>

          <p className="mt-4 max-w-2xl leading-7 text-slate-600">
            Run the live scoring and PostgreSQL
            synchronization pipeline, then reload
            this page.
          </p>

          <pre className="mt-6 overflow-x-auto rounded-2xl bg-slate-950 p-5 text-sm text-slate-100">
            bash scripts/sync_live_churn_scores_to_postgres.sh
          </pre>
        </div>
      </section>
    </main>
  );
}


export default async function AdminChurnPage({
  searchParams,
}: AdminChurnPageProps) {
  const currentUser =
    await getCurrentUser();

  if (!currentUser) {
    redirect(
      "/login?next=/admin/churn",
    );
  }

  if (currentUser.role !== "admin") {
    redirect("/");
  }

  const params = await searchParams;
  const filters = getFilters(params);

  const data = await loadDashboard(
    filters,
  );

  if (!data) {
    return <DashboardUnavailable />;
  }

  const {
    summary,
    customers,
  } = data;

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <StoreHeader />

      <section className="border-b border-slate-200 bg-slate-950 text-white">
        <div className="mx-auto max-w-7xl px-6 py-14">
          <p className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-300">
            Customer intelligence
          </p>

          <div className="mt-3 flex flex-wrap items-end justify-between gap-6">
            <div>
              <h1 className="text-4xl font-bold tracking-tight">
                Churn risk dashboard
              </h1>

              <p className="mt-4 max-w-2xl leading-7 text-slate-300">
                Prioritize retention outreach using
                point-in-time customer behavior,
                purchase recency, and model risk.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-700 bg-slate-900 px-5 py-4 text-sm">
              <p className="text-slate-400">
                Snapshot
              </p>

              <p className="mt-1 font-semibold">
                {formatDate(
                  summary.feature_snapshot_date,
                )}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-10">
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Eligible customers"
            value={
              summary.eligible_customers
            }
            detail="Customers with at least one order"
          />

          <MetricCard
            label="Predicted churners"
            value={
              summary.predicted_churners
            }
            detail={`Threshold ${formatPercent(
              summary.probability_threshold,
            )}`}
          />

          <MetricCard
            label="High-risk customers"
            value={
              summary.high_risk_customers
            }
            detail="Priority retention population"
          />

          <MetricCard
            label="Average churn probability"
            value={formatPercent(
              summary.average_churn_probability,
            )}
            detail={`Maximum ${formatPercent(
              summary.maximum_churn_probability,
            )}`}
          />
        </div>

        <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <form
            method="get"
            className="grid gap-4 lg:grid-cols-[1fr_200px_200px_auto]"
          >
            <label>
              <span className="mb-2 block text-sm font-medium text-slate-700">
                Search customer
              </span>

              <input
                name="search"
                type="search"
                defaultValue={
                  filters.search ?? ""
                }
                placeholder="Email or customer name"
                className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-950"
              />
            </label>

            <label>
              <span className="mb-2 block text-sm font-medium text-slate-700">
                Risk segment
              </span>

              <select
                name="risk_segment"
                defaultValue={
                  filters.riskSegment ?? ""
                }
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3"
              >
                <option value="">
                  All risk levels
                </option>

                <option value="high_risk">
                  High risk
                </option>

                <option value="medium_risk">
                  Medium risk
                </option>

                <option value="low_risk">
                  Low risk
                </option>
              </select>
            </label>

            <label>
              <span className="mb-2 block text-sm font-medium text-slate-700">
                Prediction
              </span>

              <select
                name="predicted_churn"
                defaultValue={
                  filters.predictedChurn
                    === undefined
                    ? ""
                    : String(
                        filters.predictedChurn,
                      )
                }
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3"
              >
                <option value="">
                  All predictions
                </option>

                <option value="true">
                  Predicted churn
                </option>

                <option value="false">
                  Not predicted churn
                </option>
              </select>
            </label>

            <div className="flex items-end gap-3">
              <button
                type="submit"
                className="rounded-xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
              >
                Apply
              </button>

              <Link
                href="/admin/churn"
                className="rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold transition hover:border-slate-950"
              >
                Reset
              </Link>
            </div>
          </form>
        </div>

        <div className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 px-6 py-5">
            <div>
              <h2 className="text-xl font-bold">
                Customer scores
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                {customers.total_items} matching
                customers
              </p>
            </div>

            <p className="text-sm text-slate-500">
              Model {summary.model_version}
            </p>
          </div>

          {customers.items.length === 0 ? (
            <div className="px-6 py-16 text-center">
              <h3 className="text-lg font-bold">
                No customers match these filters
              </h3>

              <p className="mt-2 text-slate-500">
                Reset or change the current filters.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-6 py-4">
                      Customer
                    </th>

                    <th className="px-6 py-4">
                      Orders
                    </th>

                    <th className="px-6 py-4">
                      Recency
                    </th>

                    <th className="px-6 py-4">
                      Lifetime spend
                    </th>

                    <th className="px-6 py-4">
                      Probability
                    </th>

                    <th className="px-6 py-4">
                      Risk
                    </th>

                    <th className="px-6 py-4">
                      Recommended action
                    </th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-100">
                  {customers.items.map(
                    (customer) => (
                      <tr
                        key={customer.id}
                        className="align-top"
                      >
                        <td className="px-6 py-5">
                          <Link
                            href={`/admin/churn/${customer.user_id}`}
                            className="font-semibold text-slate-950 transition hover:underline"
                          >
                            {customer.full_name}
                          </Link>

                          <p className="mt-1 text-slate-500">
                            {customer.email}
                          </p>
                        </td>

                        <td className="px-6 py-5">
                          <p className="font-semibold">
                            {customer.total_orders}
                          </p>

                          <p className="mt-1 text-xs text-slate-500">
                            {
                              customer.orders_last_90d
                            }{" "}
                            in 90 days
                          </p>
                        </td>

                        <td className="px-6 py-5">
                          <p className="font-semibold">
                            {
                              customer.days_since_last_order
                            }{" "}
                            days
                          </p>

                          <p className="mt-1 text-xs text-slate-500">
                            Since last order
                          </p>
                        </td>

                        <td className="px-6 py-5 font-semibold">
                          {formatPrice(
                            customer.lifetime_spend,
                          )}
                        </td>

                        <td className="px-6 py-5">
                          <p className="font-bold">
                            {formatPercent(
                              customer.churn_probability,
                            )}
                          </p>

                          <p className="mt-1 text-xs text-slate-500">
                            Rank {
                              customer.risk_rank
                            }
                          </p>
                        </td>

                        <td className="px-6 py-5">
                          <span
                            className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${riskClassName(
                              customer.risk_segment,
                            )}`}
                          >
                            {riskLabel(
                              customer.risk_segment,
                            )}
                          </span>

                          <p className="mt-2 text-xs text-slate-500">
                            Relative decile{" "}
                            {
                              customer.risk_decile
                            }
                          </p>
                        </td>

                        <td className="px-6 py-5">
                          <p className="font-medium">
                            {actionLabel(
                              customer.recommended_action,
                            )}
                          </p>
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          )}

          {customers.total_pages > 1 ? (
            <div className="flex items-center justify-between border-t border-slate-200 px-6 py-5">
              <p className="text-sm text-slate-500">
                Page {customers.page} of{" "}
                {customers.total_pages}
              </p>

              <div className="flex gap-3">
                {customers.page > 1 ? (
                  <Link
                    href={buildPageHref(
                      filters,
                      customers.page - 1,
                    )}
                    className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold"
                  >
                    Previous
                  </Link>
                ) : null}

                {customers.page <
                customers.total_pages ? (
                  <Link
                    href={buildPageHref(
                      filters,
                      customers.page + 1,
                    )}
                    className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold"
                  >
                    Next
                  </Link>
                ) : null}
              </div>
            </div>
          ) : null}
        </div>

        <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-sm">
          <p>
            Last scored{" "}
            <span className="font-semibold text-slate-950">
              {formatDateTime(
                summary.scored_at_utc,
              )}
            </span>
            . Risk deciles are relative rankings,
            while risk segments use the model’s
            probability threshold.
          </p>
        </div>
      </section>
    </main>
  );
}
