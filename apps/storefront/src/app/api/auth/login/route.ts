import { NextResponse } from "next/server";

import {
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


function errorRedirect(
  request: Request,
  message: string,
  redirectTo: string,
): NextResponse {
  const url = new URL("/login", request.url);

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

  const email = getFormString(
    formData,
    "email",
  ).toLowerCase();

  const password = getFormString(
    formData,
    "password",
    false,
  );

  const redirectTo = safeRedirectPath(
    getFormString(formData, "redirect_to"),
  );

  if (!email || !password) {
    return errorRedirect(
      request,
      "Email and password are required.",
      redirectTo,
    );
  }

  const result = await requestAccessToken(
    email,
    password,
  );

  if (!result.ok) {
    return errorRedirect(
      request,
      result.error,
      redirectTo,
    );
  }

  const response = NextResponse.redirect(
    new URL(redirectTo, request.url),
    {
      status: 303,
    },
  );

  setAuthenticationCookie(
    response,
    result.token,
  );

  return response;
}
