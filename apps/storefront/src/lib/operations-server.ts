import "server-only";

import {
  requestAuthenticatedApi,
} from "@/lib/api-server";
import {
  readApiError,
} from "@/lib/auth-server";
import type {
  OperationsCategoryPerformance,
  OperationsConversionFunnel,
  OperationsInventoryAlerts,
  OperationsOrderStatuses,
  OperationsRevenueTrend,
  OperationsSummary,
} from "@/lib/operations-types";


export class OperationsApiError extends Error {
  status: number;

  constructor(
    message: string,
    status: number,
  ) {
    super(message);

    this.name = "OperationsApiError";
    this.status = status;
  }
}


async function requireSuccessfulResponse(
  response: Response | null,
  fallbackMessage: string,
): Promise<Response | null> {
  if (response === null) {
    return null;
  }

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new OperationsApiError(
      await readApiError(
        response,
        fallbackMessage,
      ),
      response.status,
    );
  }

  return response;
}


export async function getOperationsSummary(
  days: number,
): Promise<OperationsSummary | null> {
  const response =
    await requireSuccessfulResponse(
      await requestAuthenticatedApi(
        (
          "/api/v1/admin/operations/"
          + `summary?days=${days}`
        ),
      ),
      "Unable to load operations summary.",
    );

  if (response === null) {
    return null;
  }

  return response.json() as Promise<
    OperationsSummary
  >;
}


export async function getOperationsRevenueTrend(
  days: number,
): Promise<OperationsRevenueTrend | null> {
  const response =
    await requireSuccessfulResponse(
      await requestAuthenticatedApi(
        (
          "/api/v1/admin/operations/"
          + `revenue-trend?days=${days}`
        ),
      ),
      "Unable to load revenue trend.",
    );

  if (response === null) {
    return null;
  }

  return response.json() as Promise<
    OperationsRevenueTrend
  >;
}


export async function getOperationsOrderStatuses(
  days: number,
): Promise<OperationsOrderStatuses | null> {
  const response =
    await requireSuccessfulResponse(
      await requestAuthenticatedApi(
        (
          "/api/v1/admin/operations/"
          + `order-statuses?days=${days}`
        ),
      ),
      "Unable to load order statuses.",
    );

  if (response === null) {
    return null;
  }

  return response.json() as Promise<
    OperationsOrderStatuses
  >;
}


export async function getOperationsCategoryPerformance(
  days: number,
): Promise<OperationsCategoryPerformance | null> {
  const response =
    await requireSuccessfulResponse(
      await requestAuthenticatedApi(
        (
          "/api/v1/admin/operations/"
          + `categories?days=${days}`
        ),
      ),
      "Unable to load category performance.",
    );

  if (response === null) {
    return null;
  }

  return response.json() as Promise<
    OperationsCategoryPerformance
  >;
}


export async function getOperationsConversionFunnel(
  days: number,
): Promise<OperationsConversionFunnel | null> {
  const response =
    await requireSuccessfulResponse(
      await requestAuthenticatedApi(
        (
          "/api/v1/admin/operations/"
          + `conversion-funnel?days=${days}`
        ),
      ),
      "Unable to load conversion funnel.",
    );

  if (response === null) {
    return null;
  }

  return response.json() as Promise<
    OperationsConversionFunnel
  >;
}


export async function getOperationsInventoryAlerts(
  {
    threshold = 10,
    page = 1,
    pageSize = 10,
  }: {
    threshold?: number;
    page?: number;
    pageSize?: number;
  } = {},
): Promise<OperationsInventoryAlerts | null> {
  const query = new URLSearchParams({
    threshold: String(threshold),
    page: String(page),
    page_size: String(pageSize),
  });

  const response =
    await requireSuccessfulResponse(
      await requestAuthenticatedApi(
        (
          "/api/v1/admin/operations/"
          + `inventory-alerts?${query.toString()}`
        ),
      ),
      "Unable to load inventory alerts.",
    );

  if (response === null) {
    return null;
  }

  return response.json() as Promise<
    OperationsInventoryAlerts
  >;
}
