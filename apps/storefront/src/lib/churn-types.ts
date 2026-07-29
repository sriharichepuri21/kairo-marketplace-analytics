export type ChurnRiskSegment =
  | "high_risk"
  | "medium_risk"
  | "low_risk";


export interface CustomerChurnScore {
  id: string;
  user_id: string;
  email: string;
  full_name: string;

  feature_snapshot_date: string;

  days_since_last_order: number;
  total_orders: number;
  orders_last_30d: number;
  orders_last_90d: number;

  lifetime_spend: string;
  average_order_value: string;
  spend_last_90d: string;
  account_age_days: number;
  is_single_order_customer: boolean;

  churn_probability: number;
  predicted_churn_flag: boolean;

  risk_rank: number;
  risk_percentile: number;
  risk_decile: number;
  risk_segment: ChurnRiskSegment;
  recommended_action: string;

  scoring_population_size: number;
  probability_threshold: number;

  model_name: string;
  model_version: string;
  scored_at_utc: string;
}


export interface CustomerChurnScorePage {
  items: CustomerChurnScore[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}


export interface CustomerChurnSummary {
  feature_snapshot_date: string;
  model_name: string;
  model_version: string;
  scored_at_utc: string;

  eligible_customers: number;
  predicted_churners: number;

  high_risk_customers: number;
  medium_risk_customers: number;
  low_risk_customers: number;

  average_churn_probability: number;
  maximum_churn_probability: number;
  probability_threshold: number;
}


export interface ChurnCustomerFilters {
  page: number;
  pageSize: number;
  riskSegment?: ChurnRiskSegment;
  predictedChurn?: boolean;
  search?: string;
}
