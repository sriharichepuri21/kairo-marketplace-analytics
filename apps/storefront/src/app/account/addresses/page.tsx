import Link from "next/link";
import { redirect } from "next/navigation";

import { StoreHeader } from "@/components/store-header";
import { getAddresses } from "@/lib/address-server";
import { getCurrentUser } from "@/lib/auth-server";


export const dynamic = "force-dynamic";

type RawSearchParams = Record<
  string,
  string | string[] | undefined
>;

interface AddressPageProps {
  searchParams: Promise<RawSearchParams>;
}


function getFirstValue(
  value: string | string[] | undefined,
): string | undefined {
  return Array.isArray(value)
    ? value[0]
    : value;
}


export default async function AddressesPage({
  searchParams,
}: AddressPageProps) {
  const currentUser = await getCurrentUser();

  if (!currentUser) {
    redirect(
      "/login?next=/account/addresses",
    );
  }

  const [addresses, params] =
    await Promise.all([
      getAddresses(),
      searchParams,
    ]);

  const message = getFirstValue(
    params.message,
  );

  const error = getFirstValue(
    params.error,
  );

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <StoreHeader />

      <section className="mx-auto max-w-7xl px-6 py-12">
        <div className="flex flex-wrap items-end justify-between gap-5">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
              Customer account
            </p>

            <h1 className="mt-2 text-4xl font-bold tracking-tight">
              Shipping addresses
            </h1>

            <p className="mt-3 text-slate-600">
              Manage the addresses available
              during checkout.
            </p>
          </div>

          <Link
            href="/cart"
            className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold transition hover:border-slate-950"
          >
            Return to cart
          </Link>
        </div>

        {message ? (
          <div className="mt-8 rounded-xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-emerald-700">
            {message}
          </div>
        ) : null}

        {error ? (
          <div className="mt-8 rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-red-700">
            {error}
          </div>
        ) : null}

        <div className="mt-10 grid gap-8 lg:grid-cols-[420px_1fr]">
          <section className="h-fit rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
            <h2 className="text-2xl font-bold">
              Add an address
            </h2>

            <p className="mt-2 text-sm leading-6 text-slate-600">
              Your first address automatically
              becomes the default.
            </p>

            <form
              action="/api/addresses"
              method="post"
              className="mt-7 space-y-4"
            >
              <input
                type="hidden"
                name="action"
                value="create"
              />

              <input
                type="hidden"
                name="return_to"
                value="/account/addresses"
              />

              <label className="block">
                <span className="text-sm font-medium">
                  Full name
                </span>

                <input
                  name="full_name"
                  type="text"
                  autoComplete="name"
                  minLength={2}
                  maxLength={160}
                  required
                  className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-950"
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium">
                  Phone
                </span>

                <input
                  name="phone"
                  type="tel"
                  autoComplete="tel"
                  minLength={7}
                  maxLength={32}
                  required
                  className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-950"
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium">
                  Address line 1
                </span>

                <input
                  name="address_line_1"
                  type="text"
                  autoComplete="address-line1"
                  minLength={3}
                  maxLength={255}
                  required
                  className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-950"
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium">
                  Address line 2
                </span>

                <input
                  name="address_line_2"
                  type="text"
                  autoComplete="address-line2"
                  maxLength={255}
                  className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-950"
                />
              </label>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block">
                  <span className="text-sm font-medium">
                    City
                  </span>

                  <input
                    name="city"
                    type="text"
                    autoComplete="address-level2"
                    minLength={2}
                    maxLength={120}
                    required
                    className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-950"
                  />
                </label>

                <label className="block">
                  <span className="text-sm font-medium">
                    State
                  </span>

                  <input
                    name="state"
                    type="text"
                    autoComplete="address-level1"
                    minLength={2}
                    maxLength={120}
                    required
                    className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-950"
                  />
                </label>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block">
                  <span className="text-sm font-medium">
                    Postal code
                  </span>

                  <input
                    name="postal_code"
                    type="text"
                    autoComplete="postal-code"
                    minLength={3}
                    maxLength={20}
                    required
                    className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-950"
                  />
                </label>

                <label className="block">
                  <span className="text-sm font-medium">
                    Country code
                  </span>

                  <input
                    name="country_code"
                    type="text"
                    autoComplete="country"
                    defaultValue="US"
                    minLength={2}
                    maxLength={2}
                    required
                    className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 uppercase outline-none focus:border-slate-950"
                  />
                </label>
              </div>

              <label className="flex items-center gap-3 text-sm">
                <input
                  name="is_default"
                  type="checkbox"
                  className="h-4 w-4"
                />

                Make this my default address
              </label>

              <button
                type="submit"
                className="w-full rounded-xl bg-slate-950 px-5 py-3 font-semibold text-white transition hover:bg-slate-800"
              >
                Add shipping address
              </button>
            </form>
          </section>

          <section>
            <h2 className="text-2xl font-bold">
              Saved addresses
            </h2>

            {!addresses ? (
              <div className="mt-5 rounded-2xl border border-red-200 bg-white p-7">
                <p className="font-semibold">
                  Addresses unavailable
                </p>

                <p className="mt-2 text-sm text-slate-600">
                  Confirm that the FastAPI service
                  is running.
                </p>
              </div>
            ) : addresses.length === 0 ? (
              <div className="mt-5 rounded-2xl border border-slate-200 bg-white p-8 text-slate-600">
                You have not saved an address yet.
              </div>
            ) : (
              <div className="mt-5 grid gap-5 md:grid-cols-2">
                {addresses.map((address) => (
                  <article
                    key={address.id}
                    className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h3 className="font-bold">
                          {address.full_name}
                        </h3>

                        <p className="mt-1 text-sm text-slate-500">
                          {address.phone}
                        </p>
                      </div>

                      {address.is_default ? (
                        <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
                          Default
                        </span>
                      ) : null}
                    </div>

                    <address className="mt-5 text-sm not-italic leading-6 text-slate-600">
                      {address.address_line_1}
                      <br />

                      {address.address_line_2 ? (
                        <>
                          {address.address_line_2}
                          <br />
                        </>
                      ) : null}

                      {address.city},{" "}
                      {address.state}{" "}
                      {address.postal_code}
                      <br />

                      {address.country_code}
                    </address>

                    <div className="mt-6 flex flex-wrap gap-2">
                      <Link
                        href={
                          `/account/addresses/` +
                          `${address.id}/edit`
                        }
                        className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold transition hover:border-slate-950"
                      >
                        Edit
                      </Link>

                      {!address.is_default ? (
                        <form
                          action="/api/addresses"
                          method="post"
                        >
                          <input
                            type="hidden"
                            name="action"
                            value="set_default"
                          />

                          <input
                            type="hidden"
                            name="address_id"
                            value={address.id}
                          />

                          <input
                            type="hidden"
                            name="return_to"
                            value="/account/addresses"
                          />

                          <button
                            type="submit"
                            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold transition hover:border-slate-950"
                          >
                            Set default
                          </button>
                        </form>
                      ) : null}

                      <form
                        action="/api/addresses"
                        method="post"
                      >
                        <input
                          type="hidden"
                          name="action"
                          value="delete"
                        />

                        <input
                          type="hidden"
                          name="address_id"
                          value={address.id}
                        />

                        <input
                          type="hidden"
                          name="return_to"
                          value="/account/addresses"
                        />

                        <button
                          type="submit"
                          className="rounded-lg px-4 py-2 text-sm font-semibold text-red-600 transition hover:bg-red-50"
                        >
                          Delete
                        </button>
                      </form>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}
