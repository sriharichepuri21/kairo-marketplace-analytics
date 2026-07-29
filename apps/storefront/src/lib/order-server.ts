import "server-only";

import {
  requestAuthenticatedApi,
} from "@/lib/api-server";
import type { Order } from "@/lib/order-types";


export async function getOrders(): Promise<
  Order[] | null
> {
  try {
    const response = await requestAuthenticatedApi(
      "/api/v1/orders",
    );

    if (!response?.ok) {
      return null;
    }

    return response.json() as Promise<Order[]>;
  } catch {
    return null;
  }
}


export type OrderLookupResult =
  | {
      status: "success";
      order: Order;
    }
  | {
      status: "not_found";
    }
  | {
      status: "unavailable";
    };


export async function getOrder(
  orderId: string,
): Promise<OrderLookupResult> {
  try {
    const response = await requestAuthenticatedApi(
      `/api/v1/orders/${orderId}`,
    );

    if (response === null) {
      return {
        status: "unavailable",
      };
    }

    if (response.status === 404) {
      return {
        status: "not_found",
      };
    }

    if (!response.ok) {
      return {
        status: "unavailable",
      };
    }

    return {
      status: "success",
      order: (await response.json()) as Order,
    };
  } catch {
    return {
      status: "unavailable",
    };
  }
}
