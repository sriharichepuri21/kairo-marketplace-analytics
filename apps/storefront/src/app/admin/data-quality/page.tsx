import Link from "next/link";
import { redirect } from "next/navigation";

import { StoreHeader } from "@/components/store-header";
import {
  getCurrentUser,
} from "@/lib/auth-server";
import {
  getDataQualityRun,
  getDataQualityRuns,
  getLatestDataQualityRun,
} from "@/lib/data-quality-server";
import type {
  DataQualityCheck,
  DataQualityCheckStatus,
  DataQualityJsonValue,
  DataQualityRunDetail,
  DataQualityRunPage,
  DataQualityRunStatus,
} from "@/lib/data-quality-types";


export const dynamic = "force-dynamic";
export const revalidate = 0;
export const fetchCache = "force-no-store";


type RawSearchParams = Record<
  string,
  string | string[] | undefined
>;


interface DataQualityPageProps {
  searchParams: Promise<RawSearchParams>;
}


interface DashboardData {
  selectedRun: DataQualityRunDetail;
  runHistory: DataQualityRunPage;
}


const uuidPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;


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
    !Number.isSafeInteger(parsed)
    || parsed < 1
  ) {
    return fallback;
  }

  return parsed;
}


function getRunId(
  value: string | undefined,
): string | undefined {
  const normalized = value?.trim();

  if (
    !normalized
    || !uuidPattern.test(normalized)
  ) {
    return undefined;
  }

  return normalized;
}


async function loadDashboard(
  page: number,
  selectedRunId: string | undefined,
): Promise<DashboardData | null> {
  try {
    const [
      selectedRun,
      runHistory,
    ] = await Promise.all([
      selectedRunId
        ? getDataQualityRun(selectedRunId)
        : getLatestDataQualityRun(),
      getDataQualityRuns({
        page,
        pageSize: 10,
      }),
    ]);

    if (
      !selectedRun
      || !runHistory
    ) {
      return null;
    }

    return {
      selectedRun,
      runHistory,
    };
  } catch (error) {
    console.error(
      "Failed to load data-quality dashboard:",
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


function formatDuration(
  startedAt: string,
  finishedAt: string | null,
): string {
  if (!finishedAt) {
    return "Still running";
  }

  const durationMilliseconds = Math.max(
    new Date(finishedAt).getTime()
      - new Date(startedAt).getTime(),
    0,
  );

  const durationSeconds =
    durationMilliseconds / 1000;

  if (durationSeconds < 1) {
    return `${Math.round(
      durationMilliseconds,
    )} ms`;
  }

  if (durationSeconds < 60) {
    return `${durationSeconds.toFixed(
      2,
    )} seconds`;
  }

  const minutes = Math.floor(
    durationSeconds / 60,
  );

  const seconds = Math.round(
    durationSeconds % 60,
  );

  return `${minutes}m ${seconds}s`;
}


function labelValue(
  value: string,
): string {
  const acronyms = new Set([
    "api",
    "gmv",
    "id",
    "sla",
    "slo",
    "sql",
    "sku",
    "utc",
  ]);

  return value
    .split("_")
    .map((part) => {
      const normalized =
        part.toLowerCase();

      if (acronyms.has(normalized)) {
        return normalized.toUpperCase();
      }

      return (
        normalized.charAt(0).toUpperCase()
        + normalized.slice(1)
      );
    })
    .join(" ");
}


function statusBadgeClassName(
  status:
    | DataQualityRunStatus
    | DataQualityCheckStatus,
): string {
  const styles = {
    running:
      "bg-sky-100 text-sky-700",
    passed:
      "bg-emerald-100 text-emerald-700",
    warning:
      "bg-amber-100 text-amber-700",
    failed:
      "bg-red-100 text-red-700",
  };

  return styles[status];
}


function statusPanelClassName(
  status: DataQualityRunStatus,
): string {
  const styles = {
    running:
      "border-sky-200 bg-sky-50",
    passed:
      "border-emerald-200 bg-emerald-50",
    warning:
      "border-amber-200 bg-amber-50",
    failed:
      "border-red-200 bg-red-50",
  };

  return styles[status];
}


function statusTextClassName(
  status: DataQualityRunStatus,
): string {
  const styles = {
    running: "text-sky-700",
    passed: "text-emerald-700",
    warning: "text-amber-700",
    failed: "text-red-700",
  };

  return styles[status];
}


function formatJsonValue(
  value: DataQualityJsonValue,
): string {
  if (value === null) {
    return "Not available";
  }

  if (
    typeof value === "string"
    || typeof value === "number"
    || typeof value === "boolean"
  ) {
    return String(value);
  }

  return JSON.stringify(
    value,
    null,
    2,
  );
}


function buildPageHref(
  page: number,
  selectedRunId?: string,
): string {
  const params = new URLSearchParams({
    page: String(page),
  });

  if (selectedRunId) {
    params.set(
      "run_id",
      selectedRunId,
    );
  }

  return (
    "/admin/data-quality?"
    + params.toString()
  );
}


function buildRunHref(
  runId: string,
  page: number,
): string {
  const params = new URLSearchParams({
    page: String(page),
    run_id: runId,
  });

  return (
    "/admin/data-quality?"
    + params.toString()
  );
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


function StatusBadge({
  status,
}: {
  status:
    | DataQualityRunStatus
    | DataQualityCheckStatus;
}) {
  return (
    <span
      className={[
        "inline-flex rounded-full px-3 py-1 text-xs font-semibold",
        statusBadgeClassName(status),
      ].join(" ")}
    >
      {labelValue(status)}
    </span>
  );
}


function CheckResultCard({
  check,
}: {
  check: DataQualityCheck;
}) {
  const hasDetails =
    Object.keys(check.details).length > 0;

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <StatusBadge
              status={check.status}
            />

            <span className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-400">
              {labelValue(
                check.check_category,
              )}
            </span>
          </div>

          <h3 className="mt-4 text-lg font-bold text-slate-950">
            {labelValue(
              check.check_name,
            )}
          </h3>

          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            {check.message
              ?? "No additional message was recorded."}
          </p>
        </div>

        <div className="text-left text-sm text-slate-500 sm:text-right">
          <p>
            Source:{" "}
            <span className="font-medium text-slate-700">
              {labelValue(
                check.check_source,
              )}
            </span>
          </p>

          <p className="mt-1">
            Target:{" "}
            <span className="font-medium text-slate-700">
              {check.target_name
                ?? "Not specified"}
            </span>
          </p>
        </div>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <div className="rounded-xl bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-400">
            Observed
          </p>

          <pre className="mt-2 whitespace-pre-wrap break-words font-sans text-sm font-medium text-slate-800">
            {formatJsonValue(
              check.observed_value,
            )}
          </pre>
        </div>

        <div className="rounded-xl bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-400">
            Expected
          </p>

          <pre className="mt-2 whitespace-pre-wrap break-words font-sans text-sm font-medium text-slate-800">
            {formatJsonValue(
              check.expected_value,
            )}
          </pre>
        </div>

        <div className="rounded-xl bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-400">
            Failures
          </p>

          <p className="mt-2 text-2xl font-bold text-slate-950">
            {formatNumber(
              check.failure_count,
            )}
          </p>
        </div>
      </div>

      {hasDetails ? (
        <details className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-slate-700">
            Technical details
          </summary>

          <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words text-xs leading-6 text-slate-600">
            {JSON.stringify(
              check.details,
              null,
              2,
            )}
          </pre>
        </details>
      ) : null}
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
            Data observability
          </p>

          <h1 className="mt-3 text-3xl font-bold">
            Data-quality results are unavailable
          </h1>

          <p className="mt-4 max-w-2xl leading-7 text-slate-600">
            Run the operational data-quality
            checks to create the first persisted
            observability snapshot.
          </p>

          <pre className="mt-6 overflow-x-auto rounded-2xl bg-slate-950 p-5 text-sm text-slate-100">
            docker compose exec -T api
            {" "}
            python -m
            {" "}
            app.scripts.run_data_quality_checks
          </pre>
        </div>
      </section>
    </main>
  );
}


export default async function DataQualityPage({
  searchParams,
}: DataQualityPageProps) {
  const currentUser =
    await getCurrentUser();

  if (!currentUser) {
    redirect(
      "/login?next=/admin/data-quality",
    );
  }

  if (currentUser.role !== "admin") {
    redirect("/");
  }

  const params = await searchParams;

  const page = getPositiveInteger(
    getFirstValue(params.page),
    1,
  );

  const selectedRunId = getRunId(
    getFirstValue(params.run_id),
  );

  const dashboard = await loadDashboard(
    page,
    selectedRunId,
  );

  if (!dashboard) {
    return <DashboardUnavailable />;
  }

  const {
    selectedRun,
    runHistory,
  } = dashboard;

  const issueChecks =
    selectedRun.checks.filter(
      (check) =>
        check.status !== "passed",
    );

  const passedChecks =
    selectedRun.checks.filter(
      (check) =>
        check.status === "passed",
    );

  const selectedRunDuration =
    formatDuration(
      selectedRun.started_at,
      selectedRun.finished_at,
    );

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <StoreHeader />

      <section className="mx-auto max-w-7xl px-6 py-10">
        <div className="flex flex-col gap-6 border-b border-slate-200 pb-8 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
              Data observability
            </p>

            <h1 className="mt-3 text-4xl font-bold tracking-tight">
              Data-quality dashboard
            </h1>

            <p className="mt-4 max-w-3xl leading-7 text-slate-600">
              Monitor freshness, completeness,
              relationships, uniqueness,
              business rules, and reconciliation
              checks across the marketplace.
            </p>
          </div>

          <nav className="flex flex-wrap gap-3">
            <Link
              href="/admin/operations"
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-slate-400"
            >
              Operations
            </Link>

            <Link
              href="/admin/churn"
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-slate-400"
            >
              Churn
            </Link>

            <Link
              href="/admin/data-quality"
              className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
            >
              Data quality
            </Link>
          </nav>
        </div>

        <section
          className={[
            "mt-8 rounded-3xl border p-8 shadow-sm",
            statusPanelClassName(
              selectedRun.status,
            ),
          ].join(" ")}
        >
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p
                className={[
                  "text-sm font-semibold uppercase tracking-[0.2em]",
                  statusTextClassName(
                    selectedRun.status,
                  ),
                ].join(" ")}
              >
                Selected run status
              </p>

              <div className="mt-3 flex flex-wrap items-center gap-4">
                <h2 className="text-3xl font-bold">
                  {selectedRun.status
                    === "passed"
                    ? "All monitored checks passed"
                    : selectedRun.status
                      === "warning"
                      ? "The platform has quality warnings"
                      : selectedRun.status
                        === "failed"
                        ? "The platform has failed checks"
                        : "Quality checks are running"}
                </h2>

                <StatusBadge
                  status={selectedRun.status}
                />
              </div>

              <p className="mt-4 text-sm leading-6 text-slate-600">
                Run started{" "}
                {formatDateTime(
                  selectedRun.started_at,
                )}
                {" · "}
                Triggered by{" "}
                <span className="font-semibold text-slate-800">
                  {labelValue(
                    selectedRun.triggered_by,
                  )}
                </span>
                {" · "}
                Duration{" "}
                <span className="font-semibold text-slate-800">
                  {selectedRunDuration}
                </span>
              </p>
            </div>

            <div className="rounded-2xl bg-white/80 px-5 py-4 text-sm shadow-sm">
              <p className="font-medium text-slate-500">
                Run identifier
              </p>

              <p className="mt-1 break-all font-mono text-xs text-slate-700">
                {selectedRun.id}
              </p>
            </div>
          </div>
        </section>

        <section className="mt-8 grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Total checks"
            value={formatNumber(
              selectedRun.total_checks,
            )}
            detail="Checks evaluated during this run"
          />

          <MetricCard
            label="Passed"
            value={formatNumber(
              selectedRun.passed_checks,
            )}
            detail="Checks meeting their expectations"
          />

          <MetricCard
            label="Warnings"
            value={formatNumber(
              selectedRun.warning_checks,
            )}
            detail="Non-critical issues requiring review"
          />

          <MetricCard
            label="Failed"
            value={formatNumber(
              selectedRun.failed_checks,
            )}
            detail="Critical data-quality violations"
          />
        </section>

        <section className="mt-10">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
                Attention required
              </p>

              <h2 className="mt-2 text-2xl font-bold">
                Warnings and failures
              </h2>
            </div>

            <p className="text-sm text-slate-500">
              {formatNumber(
                issueChecks.length,
              )}{" "}
              {issueChecks.length === 1
                ? "check requires review"
                : "checks require review"}
            </p>
          </div>

          {issueChecks.length ? (
            <div className="mt-5 space-y-5">
              {issueChecks.map(
                (check) => (
                  <CheckResultCard
                    key={check.id}
                    check={check}
                  />
                ),
              )}
            </div>
          ) : (
            <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 p-7">
              <p className="font-semibold text-emerald-800">
                No warnings or failures were
                recorded for this run.
              </p>
            </div>
          )}
        </section>

        <section className="mt-10">
          <details className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
            <summary className="cursor-pointer text-xl font-bold text-slate-950">
              Passed checks (
              {formatNumber(
                passedChecks.length,
              )}
              )
            </summary>

            <div className="mt-6 space-y-5">
              {passedChecks.map(
                (check) => (
                  <CheckResultCard
                    key={check.id}
                    check={check}
                  />
                ),
              )}
            </div>
          </details>
        </section>

        <section className="mt-10 pb-16">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
                Historical monitoring
              </p>

              <h2 className="mt-2 text-2xl font-bold">
                Quality run history
              </h2>
            </div>

            <p className="text-sm text-slate-500">
              {formatNumber(
                runHistory.total_items,
              )} persisted runs
            </p>
          </div>

          <div className="mt-5 overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-5 py-4 font-semibold text-slate-600">
                    Run
                  </th>

                  <th className="px-5 py-4 font-semibold text-slate-600">
                    Status
                  </th>

                  <th className="px-5 py-4 font-semibold text-slate-600">
                    Checks
                  </th>

                  <th className="px-5 py-4 font-semibold text-slate-600">
                    Trigger
                  </th>

                  <th className="px-5 py-4 font-semibold text-slate-600">
                    Duration
                  </th>

                  <th className="px-5 py-4 font-semibold text-slate-600">
                    Action
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {runHistory.items.map(
                  (run) => (
                    <tr
                      key={run.id}
                      className={
                        run.id
                          === selectedRun.id
                          ? "bg-slate-50"
                          : undefined
                      }
                    >
                      <td className="px-5 py-4">
                        <p className="font-semibold text-slate-900">
                          {formatDateTime(
                            run.started_at,
                          )}
                        </p>

                        <p className="mt-1 max-w-44 truncate font-mono text-xs text-slate-400">
                          {run.id}
                        </p>
                      </td>

                      <td className="px-5 py-4">
                        <StatusBadge
                          status={run.status}
                        />
                      </td>

                      <td className="px-5 py-4 text-slate-600">
                        <span className="font-semibold text-emerald-700">
                          {run.passed_checks}
                        </span>
                        {" / "}
                        <span className="font-semibold text-amber-700">
                          {run.warning_checks}
                        </span>
                        {" / "}
                        <span className="font-semibold text-red-700">
                          {run.failed_checks}
                        </span>
                      </td>

                      <td className="px-5 py-4 text-slate-600">
                        {labelValue(
                          run.triggered_by,
                        )}
                      </td>

                      <td className="px-5 py-4 text-slate-600">
                        {formatDuration(
                          run.started_at,
                          run.finished_at,
                        )}
                      </td>

                      <td className="px-5 py-4">
                        <Link
                          href={buildRunHref(
                            run.id,
                            runHistory.page,
                          )}
                          className="font-semibold text-slate-950 hover:underline"
                        >
                          View details
                        </Link>
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-5 flex items-center justify-between">
            <p className="text-sm text-slate-500">
              Page {runHistory.page} of{" "}
              {Math.max(
                runHistory.total_pages,
                1,
              )}
            </p>

            <div className="flex gap-3">
              {runHistory.page > 1 ? (
                <Link
                  href={buildPageHref(
                    runHistory.page - 1,
                    selectedRun.id,
                  )}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-slate-400"
                >
                  Previous
                </Link>
              ) : (
                <span className="rounded-xl border border-slate-200 bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-400">
                  Previous
                </span>
              )}

              {runHistory.page
                < runHistory.total_pages ? (
                  <Link
                    href={buildPageHref(
                      runHistory.page + 1,
                      selectedRun.id,
                    )}
                    className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
                  >
                    Next
                  </Link>
                ) : (
                  <span className="rounded-xl bg-slate-200 px-4 py-2 text-sm font-semibold text-slate-400">
                    Next
                  </span>
                )}
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}
