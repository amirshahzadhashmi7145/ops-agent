export interface PricingScenario {
  tickets_per_month: number;
  customer_bill_usd: number;
  vendor_cost_usd: number;
  vendor_llm_usd: number;
  vendor_hosting_usd: number;
  vendor_margin_pct: number;
  heavy_customer_bill_usd: number;
}

export interface PricingModel {
  key: "subscription" | "hybrid" | "usage" | "per_ticket";
  label: string;
  summary: string;
  scenarios: PricingScenario[];
}

export interface HostingLineItem {
  key: string;
  label: string;
  specs: string;
  monthly_usd: number;
  note: string;
}

export interface HostingStats {
  profile: string;
  source: "configured";
  currency: string;
  provider_hint: string;
  line_items: HostingLineItem[];
  monthly_usd: number;
  window_usd: number;
  window_days: number;
  assumed_capacity_tickets: number;
  at_capacity_per_ticket_usd: number;
  per_ticket_by_volume: Array<{
    tickets_per_month: number;
    hosting_per_ticket_usd: number;
    hosting_monthly_usd: number;
  }>;
  services: string[];
}

export interface UsageStats {
  days: number;
  spend_usd: number;
  spend_without_optimizations_usd: number;
  savings_usd: number;
  savings_pct: number;
  tokens: {
    prompt: number;
    completion: number;
    cached: number;
    total: number;
  };
  calls: {
    llm: number;
    semantic_hits: number;
    prompt_cache_hits: number;
    total: number;
  };
  tickets: {
    conversations: number;
    avg_cost_usd: number;
    p50_cost_usd: number;
    p90_cost_usd: number;
    p99_cost_usd: number;
    max_cost_usd: number;
    cv: number;
    cheap_share_pct: number;
    heavy_share_pct: number;
    observed: boolean;
    avg_user_turns: number;
    p90_user_turns: number;
    max_user_turns: number;
    avg_llm_calls: number;
    avg_tokens: number;
    p90_tokens: number;
    cost_per_user_turn_usd: number;
  };
  cache: {
    entries: number;
    lifetime_hits: number;
    hit_rate_pct: number;
  };
  by_model: Array<{
    model: string;
    calls: number;
    spend_usd: number;
    tokens: number;
  }>;
  by_day: Array<{
    day: string;
    spend_usd: number;
    saved_usd: number;
    calls: number;
  }>;
  decision: {
    key: PricingModel["key"] | null;
    label: string;
    confidence: "low" | "medium" | "high";
    sample: "none" | "thin" | "observed";
    why: string[];
    signals: {
      ticket_count: number;
      cost_cv: number;
      p90_vs_p50: number;
      cache_hit_rate_pct: number;
    };
  };
  hosting: HostingStats;
  pricing: {
    target_gross_margin_pct: number;
    suggested_price_per_ticket_usd: number;
    cost_per_ticket_usd: number;
    usage_this_mix_per_ticket_usd: number;
    usage_long_ticket_usd: number;
    seat_usd: number;
    included_tickets: number;
    markup: number;
    models: PricingModel[];
    model_rates: {
      model: string;
      input_per_million_usd: number;
      output_per_million_usd: number;
      cached_input_per_million_usd: number;
    };
  };
}
