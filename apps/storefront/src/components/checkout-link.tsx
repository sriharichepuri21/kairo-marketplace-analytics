"use client";

import Link from "next/link";


export function CheckoutLink() {
  function recordCheckoutStarted(): void {
    void fetch("/api/events", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        event_type: "checkout_started",
        properties: {
          source: "cart",
        },
      }),
      keepalive: true,
    }).catch(() => {
      // Analytics must never block checkout.
    });
  }

  return (
    <Link
      href="/checkout"
      onClick={recordCheckoutStarted}
      className="mt-7 block w-full rounded-xl bg-slate-950 px-5 py-3 text-center font-semibold text-white transition hover:bg-slate-800"
    >
      Proceed to checkout
    </Link>
  );
}
