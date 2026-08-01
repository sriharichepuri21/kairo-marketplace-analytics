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


export interface OperationsCategoryCurrencySummary {
  currency_code: string;
  units_sold: number;
  gross_sales: string;
  average_unit_revenue: string;
  revenue_share: number;
}


export interface OperationsCategoryPerformanceItem {
  category_id: string;
  category_name: string;
  products_sold: number;
  eligible_orders: number;
  units_sold: number;
  revenue_by_currency:
    OperationsCategoryCurrencySummary[];
}


export interface OperationsCategoryPerformance {
  days: number;
  start_date: string | null;
  end_date: string | null;
  items: OperationsCategoryPerformanceItem[];
}


export type OperationsInventoryStatus =
  | "untracked"
  | "out_of_stock"
  | "critical_stock"
  | "low_stock";


export interface OperationsInventoryAlertItem {
  product_id: string;
  product_name: string;
  sku: string | null;
  brand: string;
  category_name: string;
  available_quantity: number | null;
  reserved_quantity: number | null;
  inventory_status: OperationsInventoryStatus;
}


export interface OperationsInventoryAlerts {
  low_stock_threshold: number;

  total_products: number;
  tracked_products: number;
  untracked_products: number;
  out_of_stock_products: number;
  critical_stock_products: number;
  low_stock_products: number;
  healthy_stock_products: number;

  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;

  items: OperationsInventoryAlertItem[];
}

export interface OperationsConversionFunnel {
  days: number;
  start_date: string | null;
  end_date: string | null;

  total_sessions: number;

  product_view_sessions: number;
  add_to_cart_sessions: number;
  checkout_started_sessions: number;
  order_placed_sessions: number;

  view_dropoffs: number;
  cart_dropoffs: number;
  checkout_dropoffs: number;

  view_to_cart_rate: number;
  cart_to_checkout_rate: number;
  checkout_to_order_rate: number;
  overall_conversion_rate: number;
}

