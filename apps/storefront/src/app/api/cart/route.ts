import { NextResponse } from "next/server";

import {
  requestAuthenticatedApi,
} from "@/lib/api-server";
import {
  readApiError,
  safeRedirectPath,
} from "@/lib/auth-server";
import {
  recordCustomerEvent,
} from "@/lib/customer-event-server";
import type {
  CustomerEventInput,
} from "@/lib/customer-event-types";


type CartAction =
  | "add"
  | "update"
  | "remove"
  | "clear";


interface CartSnapshotItem {
  id: string;
  quantity: number;
  product: {
    id: string;
  };
}


interface CartSnapshot {
  items: CartSnapshotItem[];
}


function getFormString(
  formData: FormData,
  fieldName: string,
): string {
  const value = formData.get(fieldName);

  return typeof value === "string"
    ? value.trim()
    : "";
}


function redirectWithMessage(
  request: Request,
  pathname: string,
  key: "message" | "error",
  message: string,
): NextResponse {
  const url = new URL(pathname, request.url);

  url.searchParams.set(key, message);

  return NextResponse.redirect(url, {
    status: 303,
  });
}


async function loadCartSnapshot(): Promise<
  CartSnapshot | null
> {
  try {
    const response =
      await requestAuthenticatedApi(
        "/api/v1/cart",
      );

    if (!response?.ok) {
      return null;
    }

    return response.json() as Promise<CartSnapshot>;
  } catch {
    return null;
  }
}


async function recordCartEvents(
  events: CustomerEventInput[],
): Promise<void> {
  for (const event of events) {
    await recordCustomerEvent(event);
  }
}


export async function POST(
  request: Request,
): Promise<NextResponse> {
  const formData = await request.formData();

  const action = getFormString(
    formData,
    "action",
  ) as CartAction;

  const returnTo = safeRedirectPath(
    getFormString(formData, "return_to"),
  );

  let pathname: string;
  let method: "POST" | "PATCH" | "DELETE";
  let body: string | undefined;
  let successMessage: string;

  let productId = "";
  let itemId = "";
  let quantity = 0;

  switch (action) {
    case "add": {
      productId = getFormString(
        formData,
        "product_id",
      );

      quantity = Number(
        getFormString(formData, "quantity"),
      );

      if (
        !productId ||
        !Number.isInteger(quantity) ||
        quantity < 1
      ) {
        return redirectWithMessage(
          request,
          "/cart",
          "error",
          "Invalid product or quantity.",
        );
      }

      pathname = "/api/v1/cart/items";
      method = "POST";
      body = JSON.stringify({
        product_id: productId,
        quantity,
      });
      successMessage =
        "Product added to your cart.";

      break;
    }

    case "update": {
      itemId = getFormString(
        formData,
        "item_id",
      );

      quantity = Number(
        getFormString(formData, "quantity"),
      );

      if (
        !itemId ||
        !Number.isInteger(quantity) ||
        quantity < 1
      ) {
        return redirectWithMessage(
          request,
          "/cart",
          "error",
          "Invalid cart quantity.",
        );
      }

      pathname =
        `/api/v1/cart/items/${itemId}`;
      method = "PATCH";
      body = JSON.stringify({ quantity });
      successMessage = "Cart updated.";

      break;
    }

    case "remove": {
      itemId = getFormString(
        formData,
        "item_id",
      );

      if (!itemId) {
        return redirectWithMessage(
          request,
          "/cart",
          "error",
          "Invalid cart item.",
        );
      }

      pathname =
        `/api/v1/cart/items/${itemId}`;
      method = "DELETE";
      body = undefined;
      successMessage =
        "Product removed from your cart.";

      break;
    }

    case "clear":
      pathname = "/api/v1/cart";
      method = "DELETE";
      body = undefined;
      successMessage =
        "Your cart was cleared.";

      break;

    default:
      return redirectWithMessage(
        request,
        "/cart",
        "error",
        "Unknown cart action.",
      );
  }

  const requiresSnapshot =
    action === "update" ||
    action === "remove" ||
    action === "clear";

  const cartBeforeMutation =
    requiresSnapshot
      ? await loadCartSnapshot()
      : null;

  let response: Response | null;

  try {
    response = await requestAuthenticatedApi(
      pathname,
      {
        method,
        headers:
          body !== undefined
            ? {
                "Content-Type":
                  "application/json",
              }
            : undefined,
        body,
      },
    );
  } catch {
    return redirectWithMessage(
      request,
      "/cart",
      "error",
      "The cart service is currently unavailable.",
    );
  }

  if (response === null) {
    const loginUrl = new URL(
      "/login",
      request.url,
    );

    loginUrl.searchParams.set(
      "next",
      returnTo,
    );

    return NextResponse.redirect(loginUrl, {
      status: 303,
    });
  }

  if (!response.ok) {
    return redirectWithMessage(
      request,
      "/cart",
      "error",
      await readApiError(
        response,
        "Unable to update your cart.",
      ),
    );
  }

  const events: CustomerEventInput[] = [];

  if (action === "add") {
    events.push({
      event_type: "add_to_cart",
      product_id: productId,
      properties: {
        quantity,
        source: returnTo.startsWith(
          "/products/",
        )
          ? "product_detail"
          : "storefront",
      },
    });
  }

  if (
    action === "update" &&
    cartBeforeMutation
  ) {
    const previousItem =
      cartBeforeMutation.items.find(
        (item) => item.id === itemId,
      );

    if (previousItem) {
      const difference =
        quantity - previousItem.quantity;

      if (difference > 0) {
        events.push({
          event_type: "add_to_cart",
          product_id:
            previousItem.product.id,
          properties: {
            quantity: difference,
            final_quantity: quantity,
            source:
              "cart_quantity_update",
          },
        });
      }

      if (difference < 0) {
        events.push({
          event_type:
            "remove_from_cart",
          product_id:
            previousItem.product.id,
          properties: {
            quantity:
              Math.abs(difference),
            final_quantity: quantity,
            source:
              "cart_quantity_update",
          },
        });
      }
    }
  }

  if (
    action === "remove" &&
    cartBeforeMutation
  ) {
    const removedItem =
      cartBeforeMutation.items.find(
        (item) => item.id === itemId,
      );

    if (removedItem) {
      events.push({
        event_type: "remove_from_cart",
        product_id:
          removedItem.product.id,
        properties: {
          quantity: removedItem.quantity,
          source: "cart_remove",
        },
      });
    }
  }

  if (
    action === "clear" &&
    cartBeforeMutation
  ) {
    for (
      const item of cartBeforeMutation.items
    ) {
      events.push({
        event_type: "remove_from_cart",
        product_id: item.product.id,
        properties: {
          quantity: item.quantity,
          source: "cart_clear",
        },
      });
    }
  }

  await recordCartEvents(events);

  return redirectWithMessage(
    request,
    "/cart",
    "message",
    successMessage,
  );
}
