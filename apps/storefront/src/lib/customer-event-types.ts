export const CUSTOMER_EVENT_TYPES = [
  "product_view",
  "product_search",
  "add_to_cart",
  "remove_from_cart",
  "checkout_started",
  "order_placed",
] as const;

export type CustomerEventType =
  (typeof CUSTOMER_EVENT_TYPES)[number];

export interface CustomerEventInput {
  event_type: CustomerEventType;
  product_id?: string;
  order_id?: string;
  properties?: Record<string, unknown>;
}
