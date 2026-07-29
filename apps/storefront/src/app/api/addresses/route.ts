import { NextResponse } from "next/server";

import {
  readApiError,
  safeRedirectPath,
} from "@/lib/auth-server";
import {
  requestAuthenticatedApi,
} from "@/lib/api-server";


type AddressAction =
  | "create"
  | "update"
  | "set_default"
  | "delete";


function getFormString(
  formData: FormData,
  fieldName: string,
): string {
  const value = formData.get(fieldName);

  return typeof value === "string"
    ? value.trim()
    : "";
}


function getReturnPath(
  formData: FormData,
): string {
  const value = getFormString(
    formData,
    "return_to",
  );

  if (!value) {
    return "/account/addresses";
  }

  return safeRedirectPath(value);
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


function buildAddressPayload(
  formData: FormData,
): Record<string, string | boolean | null> {
  const addressLine2 = getFormString(
    formData,
    "address_line_2",
  );

  const countryCode =
    getFormString(
      formData,
      "country_code",
    ).toUpperCase() || "US";

  return {
    full_name: getFormString(
      formData,
      "full_name",
    ),
    phone: getFormString(
      formData,
      "phone",
    ),
    address_line_1: getFormString(
      formData,
      "address_line_1",
    ),
    address_line_2:
      addressLine2 || null,
    city: getFormString(
      formData,
      "city",
    ),
    state: getFormString(
      formData,
      "state",
    ),
    postal_code: getFormString(
      formData,
      "postal_code",
    ),
    country_code: countryCode,
  };
}


export async function POST(
  request: Request,
): Promise<NextResponse> {
  const formData = await request.formData();

  const action = getFormString(
    formData,
    "action",
  ) as AddressAction;

  const returnTo = getReturnPath(formData);

  let pathname: string;
  let method: "POST" | "PATCH" | "DELETE";
  let body: string | undefined;
  let successMessage: string;

  switch (action) {
    case "create": {
      const payload = buildAddressPayload(
        formData,
      );

      payload.is_default =
        formData.get("is_default") === "on";

      pathname = "/api/v1/addresses";
      method = "POST";
      body = JSON.stringify(payload);
      successMessage =
        "Shipping address added.";

      break;
    }

    case "update": {
      const addressId = getFormString(
        formData,
        "address_id",
      );

      if (!addressId) {
        return redirectWithMessage(
          request,
          returnTo,
          "error",
          "Invalid address.",
        );
      }

      const payload = buildAddressPayload(
        formData,
      );

      if (formData.has("is_default")) {
        payload.is_default = true;
      }

      pathname =
        `/api/v1/addresses/${addressId}`;

      method = "PATCH";
      body = JSON.stringify(payload);
      successMessage =
        "Shipping address updated.";

      break;
    }

    case "set_default": {
      const addressId = getFormString(
        formData,
        "address_id",
      );

      if (!addressId) {
        return redirectWithMessage(
          request,
          returnTo,
          "error",
          "Invalid address.",
        );
      }

      pathname =
        `/api/v1/addresses/${addressId}`;

      method = "PATCH";
      body = JSON.stringify({
        is_default: true,
      });
      successMessage =
        "Default shipping address updated.";

      break;
    }

    case "delete": {
      const addressId = getFormString(
        formData,
        "address_id",
      );

      if (!addressId) {
        return redirectWithMessage(
          request,
          returnTo,
          "error",
          "Invalid address.",
        );
      }

      pathname =
        `/api/v1/addresses/${addressId}`;

      method = "DELETE";
      body = undefined;
      successMessage =
        "Shipping address deleted.";

      break;
    }

    default:
      return redirectWithMessage(
        request,
        returnTo,
        "error",
        "Unknown address action.",
      );
  }

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
      returnTo,
      "error",
      "The address service is currently unavailable.",
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
      returnTo,
      "error",
      await readApiError(
        response,
        "Unable to update the address.",
      ),
    );
  }

  return redirectWithMessage(
    request,
    "/account/addresses",
    "message",
    successMessage,
  );
}
