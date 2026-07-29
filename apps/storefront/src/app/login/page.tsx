import Link from "next/link";
import { redirect } from "next/navigation";

import { StoreHeader } from "@/components/store-header";
import {
  getCurrentUser,
  safeRedirectPath,
} from "@/lib/auth-server";


export const dynamic = "force-dynamic";

type RawSearchParams = Record<
  string,
  string | string[] | undefined
>;

interface LoginPageProps {
  searchParams: Promise<RawSearchParams>;
}


function getFirstValue(
  value: string | string[] | undefined,
): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}


export default async function LoginPage({
  searchParams,
}: LoginPageProps) {
  const [params, currentUser] =
    await Promise.all([
      searchParams,
      getCurrentUser(),
    ]);

  if (currentUser) {
    redirect("/");
  }

  const error = getFirstValue(params.error);
  const message = getFirstValue(params.message);

  const redirectTo = safeRedirectPath(
    getFirstValue(params.next),
  );

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <StoreHeader />

      <section className="mx-auto flex max-w-7xl justify-center px-6 py-16">
        <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
            Customer account
          </p>

          <h1 className="mt-3 text-3xl font-bold tracking-tight">
            Log in to Kairo
          </h1>

          <p className="mt-3 text-sm leading-6 text-slate-600">
            Access your saved cart and continue shopping.
          </p>

          {error ? (
            <div className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          ) : null}

          {message ? (
            <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              {message}
            </div>
          ) : null}

          <form
            action="/api/auth/login"
            method="post"
            className="mt-8 space-y-5"
          >
            <input
              type="hidden"
              name="redirect_to"
              value={redirectTo}
            />

            <div>
              <label
                htmlFor="email"
                className="text-sm font-medium text-slate-700"
              >
                Email address
              </label>

              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-950 focus:ring-2 focus:ring-slate-200"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="text-sm font-medium text-slate-700"
              >
                Password
              </label>

              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-950 focus:ring-2 focus:ring-slate-200"
              />
            </div>

            <button
              type="submit"
              className="w-full rounded-xl bg-slate-950 px-5 py-3 font-semibold text-white transition hover:bg-slate-800"
            >
              Log in
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-600">
            New to Kairo?{" "}
            <Link
              href={
                redirectTo === "/"
                  ? "/register"
                  : `/register?next=${encodeURIComponent(
                      redirectTo,
                    )}`
              }
              className="font-semibold text-slate-950 underline-offset-4 hover:underline"
            >
              Create an account
            </Link>
          </p>
        </div>
      </section>
    </main>
  );
}
