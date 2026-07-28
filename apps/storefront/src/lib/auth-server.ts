import "server-only";

import { cookies } from "next/headers";
import type { NextResponse } from "next/server";

import type {
  AuthenticatedUser,
  TokenResponse,
} from "@/lib/auth-types";


export const AUTH_COOKIE_NAME = "kairo_access_token";

const API_URL =
  process.env.API_URL ?? "http://localhost:8000";

interface ApiValidationIssue {
  msg?: string;
}

interface ApiErrorPayload {
  detail?: string | ApiValidationIssue[];
}

interface LoginSuccess {
  ok: true;
  token: TokenResponse;
}

interface LoginFailure {
  ok: false;
  error: string;
}

export type LoginResult = LoginSuccess | LoginFailure;


export function createApiUrl(pathname: string): URL {
  return new URL(pathname, API_URL);
}


export function safeRedirectPath(
  value: string | null | undefined,
): string {
  if (
    value &&
    value.startsWith("/") &&
    !value.startsWith("//")
  ) {
    return value;
  }

  return "/";
}


export async function readApiError(
  response: Response,
  fallbackMessage: string,
): Promise<string> {
  try {
    const payload =
      (await response.json()) as ApiErrorPayload;

    if (
      typeof payload.detail === "string" &&
      payload.detail.trim()
    ) {
      return payload.detail;
    }

    if (Array.isArray(payload.detail)) {
      const messages = payload.detail
        .map((issue) => issue.msg)
        .filter(
          (message): message is string =>
            typeof message === "string",
        );

      if (messages.length > 0) {
        return messages.join(" ");
      }
    }
  } catch {
    return fallbackMessage;
  }

  return fallbackMessage;
}


export async function requestAccessToken(
  email: string,
  password: string,
): Promise<LoginResult> {
  let response: Response;

  try {
    response = await fetch(
      createApiUrl("/api/v1/auth/login"),
      {
        method: "POST",
        headers: {
          "Content-Type":
            "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({
          username: email,
          password,
        }),
        cache: "no-store",
      },
    );
  } catch {
    return {
      ok: false,
      error:
        "The authentication service is currently unavailable.",
    };
  }

  if (!response.ok) {
    return {
      ok: false,
      error: await readApiError(
        response,
        "Unable to log in.",
      ),
    };
  }

  const payload =
    (await response.json()) as Partial<TokenResponse>;

  if (
    typeof payload.access_token !== "string" ||
    typeof payload.expires_in !== "number"
  ) {
    return {
      ok: false,
      error:
        "The authentication service returned an invalid response.",
    };
  }

  return {
    ok: true,
    token: {
      access_token: payload.access_token,
      token_type: "bearer",
      expires_in: payload.expires_in,
    },
  };
}


export function setAuthenticationCookie(
  response: NextResponse,
  token: TokenResponse,
): void {
  response.cookies.set({
    name: AUTH_COOKIE_NAME,
    value: token.access_token,
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: token.expires_in,
  });
}


export async function getCurrentUser(): Promise<
  AuthenticatedUser | null
> {
  const cookieStore = await cookies();

  const token = cookieStore.get(
    AUTH_COOKIE_NAME,
  )?.value;

  if (!token) {
    return null;
  }

  let response: Response;

  try {
    response = await fetch(
      createApiUrl("/api/v1/users/me"),
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        cache: "no-store",
      },
    );
  } catch {
    return null;
  }

  if (!response.ok) {
    return null;
  }

  return response.json() as Promise<AuthenticatedUser>;
}
