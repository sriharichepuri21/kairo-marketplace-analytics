export interface OperationsCurrencySummary {
  currency_code: string;
  eligible_orders: number;
  gross_sales: string;
  average_order_value: string;
}


export interface OperationsSummary {
  days: number;
  start_date: string | null;
  end_date: string | null;
  snapshot_date: string | null;

  total_orders: number;
  eligible_orders: number;
  delivered_orders: number;
  cancelled_orders: number;
  active_customers: number;

  revenue_by_currency:
    OperationsCurrencySummary[];
}


export interface OperationsRevenueTrendPoint {
  order_date: string;
  currency_code: string;
  eligible_orders: number;
  gross_sales: string;
  average_order_value: string;
}


export interface OperationsRevenueTrend {
  days: number;
  start_date: string | null;
  end_date: string | null;
  items: OperationsRevenueTrendPoint[];
}


export interface OperationsOrderStatusItem {
  status: string;
  order_count: number;
  order_percentage: number;
}


export interface OperationsOrderStatuses {
  days: number;
  start_date: string | null;
  end_date: string | null;
  total_orders: number;
  items: OperationsOrderStatusItem[];
}
