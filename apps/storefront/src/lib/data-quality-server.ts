import "server-only";

import {
  requestAuthenticatedApi,
} from "@/lib/api-server";
import {
  readApiError,
} from "@/lib/auth-server";
import type {
  DataQualityRunDetail,
  DataQualityRunPage,
} from "@/lib/data-quality-types";


export class DataQualityApiError extends Error {
  status: number;

  constructor(
    message: string,
    status: number,
  ) {
    super(message);

    this.name = "DataQualityApiError";
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
    throw new DataQualityApiError(
      await readApiError(
        response,
        fallbackMessage,
      ),
      response.status,
    );
  }

  return response;
}


export async function getLatestDataQualityRun(): Promise<
  DataQualityRunDetail | null
> {
  const response =
    await requireSuccessfulResponse(
      await requestAuthenticatedApi(
        "/api/v1/admin/data-quality/latest",
      ),
      "Unable to load the latest data-quality run.",
    );

  if (response === null) {
    return null;
  }

  return response.json() as Promise<
    DataQualityRunDetail
  >;
}


export async function getDataQualityRun(
  runId: string,
): Promise<DataQualityRunDetail | null> {
  const response =
    await requireSuccessfulResponse(
      await requestAuthenticatedApi(
        (
          "/api/v1/admin/data-quality/runs/"
          + encodeURIComponent(runId)
        ),
      ),
      "Unable to load the selected data-quality run.",
    );

  if (response === null) {
    return null;
  }

  return response.json() as Promise<
    DataQualityRunDetail
  >;
}


export async function getDataQualityRuns(
  {
    page = 1,
    pageSize = 10,
  }: {
    page?: number;
    pageSize?: number;
  } = {},
): Promise<DataQualityRunPage | null> {
  const query = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });

  const response =
    await requireSuccessfulResponse(
      await requestAuthenticatedApi(
        (
          "/api/v1/admin/data-quality/runs"
          + `?${query.toString()}`
        ),
      ),
      "Unable to load data-quality run history.",
    );

  if (response === null) {
    return null;
  }

  return response.json() as Promise<
    DataQualityRunPage
  >;
}
