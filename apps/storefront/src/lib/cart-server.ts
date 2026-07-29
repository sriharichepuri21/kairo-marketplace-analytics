import "server-only";

import { cookies } from "next/headers";

import {
  AUTH_COOKIE_NAME,
  createApiUrl,
} from "@/lib/auth-server";
import type { Cart } from "@/lib/cart-types";


async function getAccessToken(): Promise<string | null> {
  const cookieStore = await cookies();

  return (
    cookieStore.get(AUTH_COOKIE_NAME)?.value ??
    null
  );
}


export async function requestCartApi(
  pathname: string,
  init: RequestInit = {},
): Promise<Response | null> {
  const token = await getAccessToken();

  if (!token) {
    return null;
  }

  const headers = new Headers(init.headers);

  headers.set(
    "Authorization",
    `Bearer ${token}`,
  );

  return fetch(createApiUrl(pathname), {
    ...init,
    headers,
    cache: "no-store",
  });
}


export async function getCart(): Promise<Cart | null> {
  try {
    const response = await requestCartApi(
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
