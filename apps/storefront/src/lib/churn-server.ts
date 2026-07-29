import "server-only";

import {
  readApiError,
} from "@/lib/auth-server";
import {
  requestAuthenticatedApi,
} from "@/lib/api-server";
import type {
  ChurnCustomerFilters,
  CustomerChurnScore,
  CustomerChurnScorePage,
  CustomerChurnSummary,
} from "@/lib/churn-types";


export class ChurnApiError extends Error {
  status: number;

  constructor(
    message: string,
    status: number,
  ) {
    super(message);

    this.name = "ChurnApiError";
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
    throw new ChurnApiError(
      await readApiError(
        response,
        fallbackMessage,
      ),
      response.status,
    );
  }

  return response;
}


export async function getChurnSummary(): Promise<
  CustomerChurnSummary | null
> {
  const response =
    await requireSuccessfulResponse(
      await requestAuthenticatedApi(
        "/api/v1/admin/churn/summary",
      ),
      "Unable to load the churn summary.",
    );

  if (response === null) {
    return null;
  }

  return response.json() as Promise<
    CustomerChurnSummary
  >;
}


export async function getChurnCustomers(
  filters: ChurnCustomerFilters,
): Promise<CustomerChurnScorePage | null> {
  const params = new URLSearchParams({
    page: String(filters.page),
    page_size: String(filters.pageSize),
  });

  if (filters.riskSegment) {
    params.set(
      "risk_segment",
      filters.riskSegment,
    );
  }

  if (
    filters.predictedChurn !== undefined
  ) {
    params.set(
      "predicted_churn",
      String(filters.predictedChurn),
    );
  }

  if (filters.search) {
    params.set(
      "search",
      filters.search,
    );
  }

  const response =
    await requireSuccessfulResponse(
      await requestAuthenticatedApi(
        `/api/v1/admin/churn/customers?${params.toString()}`,
      ),
      "Unable to load customer churn scores.",
    );

  if (response === null) {
    return null;
  }

  return response.json() as Promise<
    CustomerChurnScorePage
  >;
}


export async function getChurnCustomer(
  userId: string,
): Promise<CustomerChurnScore | null> {
  const response =
    await requireSuccessfulResponse(
      await requestAuthenticatedApi(
        `/api/v1/admin/churn/customers/${encodeURIComponent(
          userId,
        )}`,
      ),
      "Unable to load the customer churn score.",
    );

  if (response === null) {
    return null;
  }

  return response.json() as Promise<
    CustomerChurnScore
  >;
}
