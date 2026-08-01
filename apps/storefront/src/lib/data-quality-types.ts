export type DataQualityRunStatus =
  | "running"
  | "passed"
  | "warning"
  | "failed";


export type DataQualityCheckStatus =
  | "passed"
  | "warning"
  | "failed";


export type DataQualitySeverity =
  | "info"
  | "warning"
  | "error";


export type DataQualityJsonValue =
  | Record<string, unknown>
  | unknown[]
  | string
  | number
  | boolean
  | null;


export interface DataQualityCheck {
  id: string;
  check_name: string;
  check_category: string;
  check_source: string;
  target_name: string | null;

  status: DataQualityCheckStatus;
  severity: DataQualitySeverity;

  observed_value: DataQualityJsonValue;
  expected_value: DataQualityJsonValue;
  failure_count: number;

  message: string | null;
  details: Record<string, unknown>;

  started_at: string;
  finished_at: string | null;
  created_at: string;
}


export interface DataQualityRunSummary {
  id: string;
  run_type: string;
  status: DataQualityRunStatus;
  triggered_by: string;

  total_checks: number;
  passed_checks: number;
  warning_checks: number;
  failed_checks: number;

  started_at: string;
  finished_at: string | null;
  created_at: string;
}


export interface DataQualityRunDetail
  extends DataQualityRunSummary {
  metadata: Record<string, unknown>;
  checks: DataQualityCheck[];
}


export interface DataQualityRunPage {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;

  items: DataQualityRunSummary[];
}
