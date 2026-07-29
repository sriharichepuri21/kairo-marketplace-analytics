import { NextResponse } from "next/server";

import {
  readApiError,
} from "@/lib/auth-server";
import {
  requestAuthenticatedApi,
} from "@/lib/api-server";
import type { Order } from "@/lib/order-types";


function getFormString(
  formData: FormData,
  fieldName: string,
  trim = true,
): string {
  const value = formData.get(fieldName);

  if (typeof value !== "string") {
    return "";
  }

  return trim ? value.trim() : value;
}


function checkoutError(
  request: Request,
  message: string,
): NextResponse {
  const url = new URL("/checkout", request.url);

  url.searchParams.set("error", message);

  return NextResponse.redirect(url, {
    status: 303,
  });
}


export async function POST(
  request: Request,
): Promise<NextResponse> {
  const formData = await request.formData();

  const shippingAddressId = getFormString(
    formData,
    "shipping_address_id",
  );

  const customerNote = getFormString(
    formData,
    "customer_note",
  );

  if (!shippingAddressId) {
    return checkoutError(
      request,
      "Select a shipping address.",
    );
  }

  let response: Response | null;

  try {
    response = await requestAuthenticatedApi(
      "/api/v1/checkout",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          shipping_address_id:
            shippingAddressId,
          customer_note:
            customerNote || null,
        }),
      },
    );
  } catch {
    return checkoutError(
      request,
      "The checkout service is currently unavailable.",
    );
  }

  if (response === null) {
    const loginUrl = new URL(
      "/login",
      request.url,
    );

    loginUrl.searchParams.set(
      "next",
      "/checkout",
    );

    return NextResponse.redirect(loginUrl, {
      status: 303,
    });
  }

  if (!response.ok) {
    return checkoutError(
      request,
      await readApiError(
        response,
        "Unable to place your order.",
      ),
    );
  }

  let order: Partial<Order>;

  try {
    order =
      (await response.json()) as Partial<Order>;
  } catch {
    const ordersUrl = new URL(
      "/orders",
      request.url,
    );

    ordersUrl.searchParams.set(
      "message",
      "Your order was placed successfully.",
    );

    return NextResponse.redirect(ordersUrl, {
      status: 303,
    });
  }

  if (
    typeof order.id !== "string" ||
    !order.id
  ) {
    const ordersUrl = new URL(
      "/orders",
      request.url,
    );

    ordersUrl.searchParams.set(
      "message",
      "Your order was placed successfully.",
    );

    return NextResponse.redirect(ordersUrl, {
      status: 303,
    });
  }

  const orderUrl = new URL(
    `/orders/${order.id}`,
    request.url,
  );

  orderUrl.searchParams.set(
    "message",
    "Your order was placed successfully.",
  );

  return NextResponse.redirect(orderUrl, {
    status: 303,
  });
}
