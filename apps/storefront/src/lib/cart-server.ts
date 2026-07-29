import "server-only";

import {
  requestAuthenticatedApi,
} from "@/lib/api-server";
import type { Cart } from "@/lib/cart-types";


export async function getCart(): Promise<Cart | null> {
  try {
    const response = await requestAuthenticatedApi(
      "/api/v1/cart",
    );

    if (!response?.ok) {
      return null;
    }

    return response.json() as Promise<Cart>;
  } catch {
    return null;
  }
}
