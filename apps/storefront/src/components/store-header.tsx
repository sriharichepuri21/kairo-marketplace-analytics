import Link from "next/link";

import { getCurrentUser } from "@/lib/auth-server";


export async function StoreHeader() {
  const currentUser = await getCurrentUser();

  const firstName =
    currentUser?.full_name
      .trim()
      .split(/\s+/)[0] ?? null;

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-5 px-6 py-5">
        <Link href="/" className="block">
          <p className="text-2xl font-bold tracking-tight text-slate-950">
            Kairo
          </p>

          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
            Marketplace
          </p>
        </Link>

        <nav className="flex flex-wrap items-center justify-end gap-5 text-sm font-medium text-slate-600">
          <Link
            href="/"
            className="transition hover:text-slate-950"
          >
            Shop
          </Link>

          <Link
            href="/#catalogue"
            className="transition hover:text-slate-950"
          >
            Categories
          </Link>

          <span className="cursor-not-allowed text-slate-400">
            Orders
          </span>

          <span className="cursor-not-allowed text-slate-400">
            Cart
          </span>

          {currentUser ? (
            <>
              <span className="text-slate-950">
                Hi, {firstName}
              </span>

              <form
                action="/api/auth/logout"
                method="post"
              >
                <button
                  type="submit"
                  className="rounded-lg border border-slate-300 px-4 py-2 text-slate-700 transition hover:border-slate-950 hover:text-slate-950"
                >
                  Log out
                </button>
              </form>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="transition hover:text-slate-950"
              >
                Log in
              </Link>

              <Link
                href="/register"
                className="rounded-lg bg-slate-950 px-4 py-2 text-white transition hover:bg-slate-800"
              >
                Register
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
