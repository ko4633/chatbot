import type {
  OpportunityDetail,
  OpportunityHistoryResponse,
  OpportunityListResponse,
  UserDecisionItem,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${path} failed: ${res.status} ${body}`);
  }
  return res.json() as Promise<T>;
}

export interface OpportunityFilters {
  minScore?: number;
  minConfidence?: number;
  maxKrSellers?: number;
  status?: string;
  sortBy?: "opportunity_score" | "confidence_score" | "created_at";
  order?: "asc" | "desc";
}

export function fetchOpportunities(filters: OpportunityFilters): Promise<OpportunityListResponse> {
  const params = new URLSearchParams();
  if (filters.minScore) params.set("min_score", String(filters.minScore));
  if (filters.minConfidence) params.set("min_confidence", String(filters.minConfidence));
  if (filters.maxKrSellers !== undefined) params.set("max_kr_sellers", String(filters.maxKrSellers));
  if (filters.status) params.set("status", filters.status);
  if (filters.sortBy) params.set("sort_by", filters.sortBy);
  if (filters.order) params.set("order", filters.order);
  return apiFetch<OpportunityListResponse>(`/opportunities?${params.toString()}`);
}

export function fetchOpportunityDetail(id: string): Promise<OpportunityDetail> {
  return apiFetch<OpportunityDetail>(`/opportunities/${id}`);
}

export function fetchOpportunityHistory(id: string): Promise<OpportunityHistoryResponse> {
  return apiFetch<OpportunityHistoryResponse>(`/opportunities/${id}/history`);
}

export function postDecision(
  opportunityId: string,
  payload: { user_email: string; decision: string; reason?: string; note?: string }
): Promise<UserDecisionItem> {
  return apiFetch<UserDecisionItem>(`/opportunities/${opportunityId}/decisions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
