import { NextResponse } from "next/server";

import {
  createApiUrl,
  readApiError,
  requestAccessToken,
  safeRedirectPath,
  setAuthenticationCookie,
} from "@/lib/auth-server";


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


function registrationError(
  request: Request,
  message: string,
  redirectTo: string,
): NextResponse {
  const url = new URL("/register", request.url);

  url.searchParams.set("error", message);

  if (redirectTo !== "/") {
    url.searchParams.set("next", redirectTo);
  }

  return NextResponse.redirect(url, {
    status: 303,
  });
}


export async function POST(
  request: Request,
): Promise<NextResponse> {
  const formData = await request.formData();

  const fullName = getFormString(
    formData,
    "full_name",
  );

  const email = getFormString(
    formData,
    "email",
  ).toLowerCase();

  const password = getFormString(
    formData,
    "password",
    false,
  );

  const confirmPassword = getFormString(
    formData,
    "confirm_password",
    false,
  );

  const redirectTo = safeRedirectPath(
    getFormString(formData, "redirect_to"),
  );

  if (
    !fullName ||
    !email ||
    !password ||
    !confirmPassword
  ) {
    return registrationError(
      request,
      "Complete all required fields.",
      redirectTo,
    );
  }

  if (password !== confirmPassword) {
    return registrationError(
      request,
      "The passwords do not match.",
      redirectTo,
    );
  }

  let registrationResponse: Response;

  try {
    registrationResponse = await fetch(
      createApiUrl("/api/v1/auth/register"),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          full_name: fullName,
          password,
        }),
        cache: "no-store",
      },
    );
  } catch {
    return registrationError(
      request,
      "The registration service is currently unavailable.",
      redirectTo,
    );
  }

  if (!registrationResponse.ok) {
    return registrationError(
      request,
      await readApiError(
        registrationResponse,
        "Unable to create your account.",
      ),
      redirectTo,
    );
  }

  const loginResult = await requestAccessToken(
    email,
    password,
  );

  if (!loginResult.ok) {
    const loginUrl = new URL(
      "/login",
      request.url,
    );

    loginUrl.searchParams.set(
      "message",
      "Your account was created. Log in to continue.",
    );

    if (redirectTo !== "/") {
      loginUrl.searchParams.set(
        "next",
        redirectTo,
      );
    }

    return NextResponse.redirect(loginUrl, {
      status: 303,
    });
  }

  const response = NextResponse.redirect(
    new URL(redirectTo, request.url),
    {
      status: 303,
    },
  );

  setAuthenticationCookie(
    response,
    loginResult.token,
  );

  return response;
}
