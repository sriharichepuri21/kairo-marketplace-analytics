import { NextResponse } from "next/server";

import { AUTH_COOKIE_NAME } from "@/lib/auth-server";


export async function POST(
  request: Request,
): Promise<NextResponse> {
  const response = NextResponse.redirect(
    new URL("/", request.url),
    {
      status: 303,
    },
  );

  response.cookies.delete(
    AUTH_COOKIE_NAME,
  );

  return response;
}
