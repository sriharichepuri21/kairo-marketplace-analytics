import { NextResponse } from "next/server";

import {
  sendCustomerEvent,
} from "@/lib/customer-event-server";
import {
  CUSTOMER_EVENT_TYPES,
} from "@/lib/customer-event-types";
import type {
  CustomerEventInput,
} from "@/lib/customer-event-types";


const supportedEventTypes = new Set<string>(
  CUSTOMER_EVENT_TYPES,
);


function isRecord(
  value: unknown,
): value is Record<string, unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}


export async function POST(
  request: Request,
): Promise<NextResponse> {
  let payload: unknown;

  try {
    payload = await request.json();
  } catch {
    return NextResponse.json(
      {
        detail: "Invalid JSON request body.",
      },
      {
        status: 400,
      },
    );
  }

  if (
    !isRecord(payload) ||
    typeof payload.event_type !== "string" ||
    !supportedEventTypes.has(
      payload.event_type,
    )
  ) {
    return NextResponse.json(
      {
        detail:
          "A supported event_type is required.",
      },
      {
        status: 422,
      },
    );
  }

  const event: CustomerEventInput = {
    event_type:
      payload.event_type as CustomerEventInput["event_type"],
  };

  if (typeof payload.product_id === "string") {
    event.product_id = payload.product_id;
  }

  if (typeof payload.order_id === "string") {
    event.order_id = payload.order_id;
  }

  if (isRecord(payload.properties)) {
    event.properties = payload.properties;
  }

  let upstreamResponse: Response;

  try {
    upstreamResponse =
      await sendCustomerEvent(event);
  } catch {
    return NextResponse.json(
      {
        detail:
          "The customer event service is unavailable.",
      },
      {
        status: 503,
      },
    );
  }

  const responseBody =
    await upstreamResponse.text();

  const contentType =
    upstreamResponse.headers.get(
      "content-type",
    );

  return new NextResponse(
    responseBody || null,
    {
      status: upstreamResponse.status,
      headers: contentType
        ? {
            "Content-Type": contentType,
          }
        : undefined,
    },
  );
}
