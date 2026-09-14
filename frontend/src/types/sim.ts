export interface SimSubscription {
  id: string;
  customer_id: string;
  plan_name: string;
  status: string;
  monthly_price_usd: string;
  cancelled_at?: string | null;
}

export interface SimDevice {
  id: string;
  customer_id: string;
  serial_number: string;
  model: string;
  status: string;
  purchase_date?: string | null;
  return_reason?: string | null;
}

export interface SimCustomerCatalog {
  id: string;
  email: string;
  full_name: string;
  phone?: string | null;
  subscriptions: SimSubscription[];
  devices: SimDevice[];
}

export interface SimOrder {
  id: string;
  customer_id: string;
  order_number: string;
  channel: string;
  customer_email: string;
  order_date: string;
  delivery_date: string;
  fulfillment_status: string;
  delivery_status?: string | null;
  deliver_by?: string | null;
  tags?: string[] | null;
  shipping_name: string;
  shipping_line1: string;
  shipping_line2?: string | null;
  shipping_city: string;
  shipping_state: string;
  shipping_postal_code: string;
  shipping_country: string;
  phone: string;
  return_status: string;
  refund_status: string;
  return_reason?: string | null;
  rma_url?: string | null;
  tracking_number?: string | null;
}

export interface SimDeviceProfileSummary {
  serial_number: string;
  customer_email: string;
  segment: string;
  camera_family: string;
  model: string;
  sim_triage_conclusion?: string | null;
  health_score?: string | null;
}

export interface SimCatalog {
  customers: SimCustomerCatalog[];
  orders?: SimOrder[];
  device_profiles?: SimDeviceProfileSummary[];
  outbound_messages?: Array<{
    id: string;
    to_address: string;
    subject: string;
    related_entity_type?: string | null;
    message_kind?: string | null;
    created_at?: string | null;
  }>;
}
