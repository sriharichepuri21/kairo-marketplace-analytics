import Link from "next/link";
import {
  notFound,
  redirect,
} from "next/navigation";

import { StoreHeader } from "@/components/store-header";
import {
  getCurrentUser,
} from "@/lib/auth-server";
import {
  getChurnCustomer,
} from "@/lib/churn-server";
import type {
  ChurnRiskSegment,
  CustomerChurnScore,
} from "@/lib/churn-types";
import { formatPrice } from "@/lib/format";


export const dynamic = "force-dynamic";


interface CustomerChurnPageProps {
  params: Promise<{
    userId: string;
  }>;
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
      "border-red-200 bg-red-50 text-red-700",
    medium_risk:
      "border-amber-200 bg-amber-50 text-amber-700",
    low_risk:
      "border-emerald-200 bg-emerald-50 text-emerald-700",
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


function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string | number;
  detail?: string;
}) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-sm font-medium text-slate-500">
        {label}
      </p>

      <p className="mt-3 text-2xl font-bold text-slate-950">
        {value}
      </p>

      {detail ? (
        <p className="mt-2 text-sm text-slate-500">
          {detail}
        </p>
      ) : null}
    </article>
  );
}


function explainRisk(
  customer: CustomerChurnScore,
): string {
  if (
    customer.risk_segment === "high_risk"
  ) {
    return (
      "This customer exceeded the production churn "
      + "probability threshold and should be prioritized "
      + "for retention outreach."
    );
  }

  if (
    customer.risk_segment === "medium_risk"
  ) {
    return (
      "This customer has elevated churn risk but remains "
      + "below the production classification threshold."
    );
  }

  return (
    "This customer currently has a low absolute churn "
    + "probability. Continue standard monitoring."
  );
}


export default async function CustomerChurnPage({
  params,
}: CustomerChurnPageProps) {
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

  const {
    userId,
  } = await params;

  let customer: CustomerChurnScore | null;

  try {
    customer =
      await getChurnCustomer(userId);
  } catch (error) {
    console.error(
      "Failed to load customer churn score:",
      error,
    );

    customer = null;
  }

  if (!customer) {
    notFound();
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <StoreHeader />

      <section className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-6 py-10">
          <Link
            href="/admin/churn"
            className="text-sm font-semibold text-slate-600 transition hover:text-slate-950"
          >
            ← Back to churn dashboard
          </Link>

          <div className="mt-6 flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
                Customer intelligence
              </p>

              <h1 className="mt-3 text-4xl font-bold tracking-tight">
                {customer.full_name}
              </h1>

              <p className="mt-2 text-slate-600">
                {customer.email}
              </p>
            </div>

            <div
              className={`rounded-2xl border px-6 py-4 ${riskClassName(
                customer.risk_segment,
              )}`}
            >
              <p className="text-sm font-medium">
                Current classification
              </p>

              <p className="mt-1 text-2xl font-bold">
                {riskLabel(
                  customer.risk_segment,
                )}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-10">
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
          <Metric
            label="Churn probability"
            value={formatPercent(
              customer.churn_probability,
            )}
            detail={`Classification threshold ${formatPercent(
              customer.probability_threshold,
            )}`}
          />

          <Metric
            label="Total orders"
            value={customer.total_orders}
            detail={`${customer.orders_last_90d} orders in the last 90 days`}
          />

          <Metric
            label="Days since last order"
            value={customer.days_since_last_order}
            detail="Purchase-recency feature"
          />

          <Metric
            label="Lifetime spend"
            value={formatPrice(
              customer.lifetime_spend,
            )}
            detail={`Average order ${formatPrice(
              customer.average_order_value,
            )}`}
          />
        </div>

        <div className="mt-8 grid gap-8 lg:grid-cols-[1.25fr_0.75fr]">
          <section className="rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
            <h2 className="text-2xl font-bold">
              Risk explanation
            </h2>

            <p className="mt-4 leading-7 text-slate-600">
              {explainRisk(customer)}
            </p>

            <div className="mt-7 grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl bg-slate-50 p-5">
                <p className="text-sm text-slate-500">
                  Absolute risk segment
                </p>

                <p className="mt-2 font-bold">
                  {riskLabel(
                    customer.risk_segment,
                  )}
                </p>
              </div>

              <div className="rounded-xl bg-slate-50 p-5">
                <p className="text-sm text-slate-500">
                  Relative population rank
                </p>

                <p className="mt-2 font-bold">
                  Rank {customer.risk_rank} of{" "}
                  {
                    customer.scoring_population_size
                  }
                </p>
              </div>

              <div className="rounded-xl bg-slate-50 p-5">
                <p className="text-sm text-slate-500">
                  Relative risk decile
                </p>

                <p className="mt-2 font-bold">
                  Decile {
                    customer.risk_decile
                  }
                </p>
              </div>

              <div className="rounded-xl bg-slate-50 p-5">
                <p className="text-sm text-slate-500">
                  Account age
                </p>

                <p className="mt-2 font-bold">
                  {
                    customer.account_age_days
                  }{" "}
                  days
                </p>
              </div>
            </div>
          </section>

          <aside className="rounded-2xl border border-slate-200 bg-slate-950 p-7 text-white shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">
              Recommended action
            </p>

            <h2 className="mt-4 text-2xl font-bold">
              {actionLabel(
                customer.recommended_action,
              )}
            </h2>

            <p className="mt-4 leading-7 text-slate-300">
              Use this recommendation as a prioritization
              signal. It should support, not replace,
              customer-service or marketing judgment.
            </p>

            <div className="mt-7 border-t border-slate-700 pt-6 text-sm text-slate-400">
              <p>
                Model: {customer.model_version}
              </p>

              <p className="mt-2">
                Snapshot:{" "}
                {formatDate(
                  customer.feature_snapshot_date,
                )}
              </p>

              <p className="mt-2">
                Scored:{" "}
                {formatDateTime(
                  customer.scored_at_utc,
                )}
              </p>
            </div>
          </aside>
        </div>

        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
          <h2 className="text-2xl font-bold">
            Production feature values
          </h2>

          <div className="mt-6 overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-4">
                    Feature
                  </th>

                  <th className="px-5 py-4">
                    Value
                  </th>

                  <th className="px-5 py-4">
                    Meaning
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                <tr>
                  <td className="px-5 py-4 font-medium">
                    Days since last order
                  </td>

                  <td className="px-5 py-4">
                    {
                      customer.days_since_last_order
                    }
                  </td>

                  <td className="px-5 py-4 text-slate-500">
                    Purchase recency
                  </td>
                </tr>

                <tr>
                  <td className="px-5 py-4 font-medium">
                    Total orders
                  </td>

                  <td className="px-5 py-4">
                    {customer.total_orders}
                  </td>

                  <td className="px-5 py-4 text-slate-500">
                    Lifetime purchase frequency
                  </td>
                </tr>

                <tr>
                  <td className="px-5 py-4 font-medium">
                    Orders in 30 days
                  </td>

                  <td className="px-5 py-4">
                    {
                      customer.orders_last_30d
                    }
                  </td>

                  <td className="px-5 py-4 text-slate-500">
                    Recent purchase activity
                  </td>
                </tr>

                <tr>
                  <td className="px-5 py-4 font-medium">
                    Orders in 90 days
                  </td>

                  <td className="px-5 py-4">
                    {
                      customer.orders_last_90d
                    }
                  </td>

                  <td className="px-5 py-4 text-slate-500">
                    Medium-term purchase activity
                  </td>
                </tr>

                <tr>
                  <td className="px-5 py-4 font-medium">
                    Account age
                  </td>

                  <td className="px-5 py-4">
                    {
                      customer.account_age_days
                    }{" "}
                    days
                  </td>

                  <td className="px-5 py-4 text-slate-500">
                    Customer relationship tenure
                  </td>
                </tr>

                <tr>
                  <td className="px-5 py-4 font-medium">
                    Single-order customer
                  </td>

                  <td className="px-5 py-4">
                    {
                      customer.is_single_order_customer
                        ? "Yes"
                        : "No"
                    }
                  </td>

                  <td className="px-5 py-4 text-slate-500">
                    Indicates limited repeat-purchase history
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </main>
  );
}
