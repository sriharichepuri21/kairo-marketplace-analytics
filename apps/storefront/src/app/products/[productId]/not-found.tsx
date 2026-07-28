import Link from "next/link";

import { StoreHeader } from "@/components/store-header";

export default function ProductNotFound() {
  return (
    <main className="min-h-screen bg-slate-50">
      <StoreHeader />

      <div className="mx-auto flex max-w-7xl justify-center px-6 py-24">
        <div className="max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
            404
          </p>

          <h1 className="mt-3 text-3xl font-bold text-slate-950">
            Product not found
          </h1>

          <p className="mt-3 text-slate-600">
            The requested product does not exist or is no longer active.
          </p>

          <Link
            href="/"
            className="mt-6 inline-block rounded-xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white"
          >
            Browse products
          </Link>
        </div>
      </div>
    </main>
  );
}
