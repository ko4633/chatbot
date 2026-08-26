// Mirrors apps/api/schemas/opportunity.py. Kept in sync by hand in Phase 1;
// docs/EVALUATION.md §4 (contract tests) pins the API shape server-side so
// drift shows up as a failing test, not a silent runtime mismatch.

export interface OpportunityListItem {
  id: string;
  product_id: string;
  product_title: string;
  opportunity_score: number;
  confidence_score: number;
  market_pair: string;
  japan_purchase_price_jpy: number;
  korea_sale_price_krw: number;
  expected_margin_krw: number;
  kr_seller_count: number;
  status: string;
  is_mock: boolean;
  created_at: string;
}

export interface OpportunityListResponse {
  items: OpportunityListItem[];
  total: number;
  data_mode: "mock" | "live" | "mixed";
}

export interface OfferSummary {
  offer_id: string;
  listing_url: string;
  seller_name: string | null;
  title_raw: string | null;
  latest_price: number | null;
  currency_code: string;
  in_stock: boolean | null;
}

export interface PriceHistoryPoint {
  observed_at: string;
  price_amount: number;
  currency_code: string;
  source_snapshot_id: string | null;
}

export interface EntityMatchEvidenceItem {
  id: string;
  left_variant_id: string;
  right_variant_id: string;
  left_title: string;
  right_title: string;
  match_type: string;
  match_stage: string;
  match_confidence: number;
  evidence: Record<string, unknown>;
  algorithm_version: string;
}

export interface EventItem {
  id: string;
  event_type: string;
  previous_value: Record<string, unknown>;
  new_value: Record<string, unknown>;
  change_pct: number | null;
  observed_at: string;
  confidence: number;
}

export interface InsightItem {
  id: string;
  title: string;
  narrative: string;
  is_ai_generated: boolean;
  confidence: number;
}

export interface SourceRef {
  id: string;
  name: string;
  source_type: string;
  trust_tier: string;
  factual_reliability: string;
  signal_value: string;
  is_mock: boolean;
  base_url: string | null;
}

export interface UserDecisionItem {
  id: string;
  decision: string;
  reason: string | null;
  note: string | null;
  created_at: string;
}

export interface OpportunityDetail {
  id: string;
  product_id: string;
  product_title: string;
  opportunity_type: string;
  opportunity_score: number;
  confidence_score: number;
  sub_scores: {
    weighted_components: Record<string, { score: number; weight: number; contribution: number }>;
    confidence_components: Record<string, number>;
  };
  weights_version: string;
  economics: Record<string, number | string>;
  regulation_status: string;
  regulation_basis: string | null;
  status: string;
  created_at: string;
  analysis_run_id: string;
  japan_offers: OfferSummary[];
  korea_offers: OfferSummary[];
  price_history_jp: PriceHistoryPoint[];
  price_history_kr: PriceHistoryPoint[];
  entity_matches: EntityMatchEvidenceItem[];
  events: EventItem[];
  insights: InsightItem[];
  sources: SourceRef[];
  decisions: UserDecisionItem[];
  is_mock: boolean;
}
