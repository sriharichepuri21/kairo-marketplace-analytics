import Link from "next/link";

import { StoreHeader } from "@/components/store-header";


export default function OrderNotFound() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <StoreHeader />

      <section className="mx-auto max-w-3xl px-6 py-16">
        <div className="rounded-3xl border border-slate-200 bg-white p-10 text-center shadow-sm">
          <h1 className="text-3xl font-bold">
            Order not found
          </h1>

          <p className="mt-4 text-slate-600">
            This order does not exist or does not
            belong to your account.
          </p>

          <Link
            href="/orders"
            className="mt-7 inline-block rounded-xl bg-slate-950 px-6 py-3 font-semibold text-white"
          >
            View your orders
          </Link>
        </div>
      </section>
    </main>
  );
}
