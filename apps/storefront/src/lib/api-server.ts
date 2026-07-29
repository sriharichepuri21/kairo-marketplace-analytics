import "server-only";

import { cookies } from "next/headers";

import {
  AUTH_COOKIE_NAME,
  createApiUrl,
} from "@/lib/auth-server";


export async function requestAuthenticatedApi(
  pathname: string,
  init: RequestInit = {},
): Promise<Response | null> {
  const cookieStore = await cookies();

  const accessToken = cookieStore.get(
    AUTH_COOKIE_NAME,
  )?.value;

  if (!accessToken) {
    return null;
  }

  const headers = new Headers(init.headers);

  headers.set(
    "Authorization",
    `Bearer ${accessToken}`,
  );

  return fetch(createApiUrl(pathname), {
    ...init,
    headers,
    cache: "no-store",
  });
}
