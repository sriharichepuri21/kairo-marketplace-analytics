import Link from "next/link";
import { redirect } from "next/navigation";

import { StoreHeader } from "@/components/store-header";
import { getAddress } from "@/lib/address-server";
import { getCurrentUser } from "@/lib/auth-server";


export const dynamic = "force-dynamic";

interface EditAddressPageProps {
  params: Promise<{
    addressId: string;
  }>;
}


export default async function EditAddressPage({
  params,
}: EditAddressPageProps) {
  const currentUser = await getCurrentUser();

  if (!currentUser) {
    redirect(
      "/login?next=/account/addresses",
    );
  }

  const { addressId } = await params;

  const address = await getAddress(addressId);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <StoreHeader />

      <section className="mx-auto max-w-3xl px-6 py-12">
        <Link
          href="/account/addresses"
          className="text-sm font-semibold text-slate-600 hover:text-slate-950"
        >
          ← Back to addresses
        </Link>

        {!address ? (
          <div className="mt-8 rounded-2xl border border-red-200 bg-white p-8">
            <h1 className="text-2xl font-bold">
              Address unavailable
            </h1>

            <p className="mt-3 text-slate-600">
              The address could not be found or
              does not belong to this account.
            </p>
          </div>
        ) : (
          <div className="mt-8 rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
              Customer account
            </p>

            <h1 className="mt-2 text-3xl font-bold">
              Edit shipping address
            </h1>

            <form
              action="/api/addresses"
              method="post"
              className="mt-8 space-y-5"
            >
              <input
                type="hidden"
                name="action"
                value="update"
              />

              <input
                type="hidden"
                name="address_id"
                value={address.id}
              />

              <input
                type="hidden"
                name="return_to"
                value={
                  `/account/addresses/` +
                  `${address.id}/edit`
                }
              />

              <label className="block">
                <span className="text-sm font-medium">
                  Full name
                </span>

                <input
                  name="full_name"
                  type="text"
                  defaultValue={address.full_name}
                  minLength={2}
                  maxLength={160}
                  required
                  className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3"
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium">
                  Phone
                </span>

                <input
                  name="phone"
                  type="tel"
                  defaultValue={address.phone}
                  minLength={7}
                  maxLength={32}
                  required
                  className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3"
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium">
                  Address line 1
                </span>

                <input
                  name="address_line_1"
                  type="text"
                  defaultValue={
                    address.address_line_1
                  }
                  minLength={3}
                  maxLength={255}
                  required
                  className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3"
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium">
                  Address line 2
                </span>

                <input
                  name="address_line_2"
                  type="text"
                  defaultValue={
                    address.address_line_2 ?? ""
                  }
                  maxLength={255}
                  className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3"
                />
              </label>

              <div className="grid gap-5 sm:grid-cols-2">
                <label className="block">
                  <span className="text-sm font-medium">
                    City
                  </span>

                  <input
                    name="city"
                    type="text"
                    defaultValue={address.city}
                    required
                    className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3"
                  />
                </label>

                <label className="block">
                  <span className="text-sm font-medium">
                    State
                  </span>

                  <input
                    name="state"
                    type="text"
                    defaultValue={address.state}
                    required
                    className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3"
                  />
                </label>
              </div>

              <div className="grid gap-5 sm:grid-cols-2">
                <label className="block">
                  <span className="text-sm font-medium">
                    Postal code
                  </span>

                  <input
                    name="postal_code"
                    type="text"
                    defaultValue={
                      address.postal_code
                    }
                    required
                    className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3"
                  />
                </label>

                <label className="block">
                  <span className="text-sm font-medium">
                    Country code
                  </span>

                  <input
                    name="country_code"
                    type="text"
                    defaultValue={
                      address.country_code
                    }
                    minLength={2}
                    maxLength={2}
                    required
                    className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 uppercase"
                  />
                </label>
              </div>

              {!address.is_default ? (
                <label className="flex items-center gap-3 text-sm">
                  <input
                    name="is_default"
                    type="checkbox"
                    className="h-4 w-4"
                  />

                  Make this my default address
                </label>
              ) : (
                <p className="rounded-xl bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">
                  This is your current default
                  address.
                </p>
              )}

              <button
                type="submit"
                className="w-full rounded-xl bg-slate-950 px-5 py-3 font-semibold text-white transition hover:bg-slate-800"
              >
                Save address
              </button>
            </form>
          </div>
        )}
      </section>
    </main>
  );
}
