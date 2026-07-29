import "server-only";

import {
  requestAuthenticatedApi,
} from "@/lib/api-server";
import type { Address } from "@/lib/address-types";


export async function getAddresses(): Promise<
  Address[] | null
> {
  try {
    const response = await requestAuthenticatedApi(
      "/api/v1/addresses",
    );

    if (!response?.ok) {
      return null;
    }

    return response.json() as Promise<Address[]>;
  } catch {
    return null;
  }
}


export async function getAddress(
  addressId: string,
): Promise<Address | null> {
  try {
    const response = await requestAuthenticatedApi(
      `/api/v1/addresses/${addressId}`,
    );

    if (!response?.ok) {
      return null;
    }

    return response.json() as Promise<Address>;
  } catch {
    return null;
  }
}
