import { NextResponse } from "next/server";

import {
  readApiError,
  safeRedirectPath,
} from "@/lib/auth-server";
import { requestAuthenticatedApi } from "@/lib/api-server";


type CartAction =
  | "add"
  | "update"
  | "remove"
  | "clear";


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

  switch (action) {
    case "add": {
      const productId = getFormString(
        formData,
        "product_id",
      );

      const quantity = Number(
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
      const itemId = getFormString(
        formData,
        "item_id",
      );

      const quantity = Number(
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

      pathname = `/api/v1/cart/items/${itemId}`;
      method = "PATCH";
      body = JSON.stringify({ quantity });
      successMessage = "Cart updated.";

      break;
    }

    case "remove": {
      const itemId = getFormString(
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

      pathname = `/api/v1/cart/items/${itemId}`;
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
      successMessage = "Your cart was cleared.";

      break;

    default:
      return redirectWithMessage(
        request,
        "/cart",
        "error",
        "Unknown cart action.",
      );
  }

  let response: Response | null;

  try {
    response = await requestAuthenticatedApi(pathname, {
      method,
      headers:
        body !== undefined
          ? {
              "Content-Type": "application/json",
            }
          : undefined,
      body,
    });
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

  return redirectWithMessage(
    request,
    "/cart",
    "message",
    successMessage,
  );
}
