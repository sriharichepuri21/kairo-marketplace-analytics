import "server-only";

import { randomUUID } from "node:crypto";

import { cookies } from "next/headers";

import {
  AUTH_COOKIE_NAME,
  createApiUrl,
} from "@/lib/auth-server";
import type {
  CustomerEventInput,
} from "@/lib/customer-event-types";


export const CUSTOMER_SESSION_COOKIE_NAME =
  "kairo_customer_session";

const CUSTOMER_SESSION_MAX_AGE =
  60 * 60 * 24 * 365;


function isValidSessionId(
  value: string | undefined,
): value is string {
  return Boolean(
    value &&
      value.length >= 8 &&
      value.length <= 128 &&
      /^[A-Za-z0-9_-]+$/.test(value),
  );
}


async function getOrCreateSessionId(): Promise<string> {
  const cookieStore = await cookies();

  const existingSessionId = cookieStore.get(
    CUSTOMER_SESSION_COOKIE_NAME,
  )?.value;

  if (isValidSessionId(existingSessionId)) {
    return existingSessionId;
  }

  const sessionId = randomUUID();

  cookieStore.set({
    name: CUSTOMER_SESSION_COOKIE_NAME,
    value: sessionId,
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: CUSTOMER_SESSION_MAX_AGE,
  });

  return sessionId;
}


export async function sendCustomerEvent(
  event: CustomerEventInput,
): Promise<Response> {
  const cookieStore = await cookies();

  const sessionId =
    await getOrCreateSessionId();

  const accessToken = cookieStore.get(
    AUTH_COOKIE_NAME,
  )?.value;

  const headers = new Headers({
    "Content-Type": "application/json",
  });

  if (accessToken) {
    headers.set(
      "Authorization",
      `Bearer ${accessToken}`,
    );
  }

  return fetch(
    createApiUrl("/api/v1/events"),
    {
      method: "POST",
      headers,
      body: JSON.stringify({
        ...event,
        session_id: sessionId,
      }),
      cache: "no-store",
    },
  );
}


export async function recordCustomerEvent(
  event: CustomerEventInput,
): Promise<void> {
  try {
    const response =
      await sendCustomerEvent(event);

    if (!response.ok) {
      console.warn(
        "Customer event was rejected:",
        event.event_type,
        response.status,
      );
    }
  } catch (error) {
    console.warn(
      "Customer event service unavailable:",
      event.event_type,
      error,
    );
  }
}
