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

interface RegisterPageProps {
  searchParams: Promise<RawSearchParams>;
}


function getFirstValue(
  value: string | string[] | undefined,
): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}


export default async function RegisterPage({
  searchParams,
}: RegisterPageProps) {
  const [params, currentUser] =
    await Promise.all([
      searchParams,
      getCurrentUser(),
    ]);

  if (currentUser) {
    redirect("/");
  }

  const error = getFirstValue(params.error);

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
            Create your account
          </h1>

          <p className="mt-3 text-sm leading-6 text-slate-600">
            Register to save products in a persistent shopping cart.
          </p>

          {error ? (
            <div className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          ) : null}

          <form
            action="/api/auth/register"
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
                htmlFor="full_name"
                className="text-sm font-medium text-slate-700"
              >
                Full name
              </label>

              <input
                id="full_name"
                name="full_name"
                type="text"
                autoComplete="name"
                minLength={2}
                maxLength={160}
                required
                className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-950 focus:ring-2 focus:ring-slate-200"
              />
            </div>

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
                autoComplete="new-password"
                minLength={8}
                maxLength={128}
                required
                className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-950 focus:ring-2 focus:ring-slate-200"
              />
            </div>

            <div>
              <label
                htmlFor="confirm_password"
                className="text-sm font-medium text-slate-700"
              >
                Confirm password
              </label>

              <input
                id="confirm_password"
                name="confirm_password"
                type="password"
                autoComplete="new-password"
                minLength={8}
                maxLength={128}
                required
                className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-950 focus:ring-2 focus:ring-slate-200"
              />
            </div>

            <button
              type="submit"
              className="w-full rounded-xl bg-slate-950 px-5 py-3 font-semibold text-white transition hover:bg-slate-800"
            >
              Create account
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-600">
            Already registered?{" "}
            <Link
              href={
                redirectTo === "/"
                  ? "/login"
                  : `/login?next=${encodeURIComponent(
                      redirectTo,
                    )}`
              }
              className="font-semibold text-slate-950 underline-offset-4 hover:underline"
            >
              Log in
            </Link>
          </p>
        </div>
      </section>
    </main>
  );
}
