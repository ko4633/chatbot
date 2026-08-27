"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchOpportunities, type OpportunityFilters } from "@/lib/api";
import type { OpportunityListItem, OpportunityListResponse } from "@/lib/types";

function scoreClass(score: number): string {
  if (score >= 65) return "high";
  if (score >= 45) return "mid";
  return "low";
}

export default function TodaysIntelligencePage() {
  const [data, setData] = useState<OpportunityListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<OpportunityFilters>({
    minScore: 0,
    minConfidence: 0,
    sortBy: "opportunity_score",
    order: "desc",
  });

  useEffect(() => {
    let cancelled = false;
    fetchOpportunities(filters)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [filters]);

  const items = useMemo(() => data?.items ?? [], [data]);

  function toggleSort(field: OpportunityFilters["sortBy"]) {
    setFilters((f) => ({
      ...f,
      sortBy: field,
      order: f.sortBy === field && f.order === "desc" ? "asc" : "desc",
    }));
  }

  return (
    <main className="container">
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 16 }}>
        <h2 style={{ margin: 0, fontSize: 18 }}>Today&apos;s Intelligence</h2>
        {data && data.data_mode !== "live" && (
          <span className="mock-badge">{data.data_mode.toUpperCase()} DATA</span>
        )}
      </div>

      <div className="filters">
        <label>
          Min Score
          <input
            type="number"
            min={0}
            max={100}
            value={filters.minScore}
            onChange={(e) => setFilters((f) => ({ ...f, minScore: Number(e.target.value) }))}
            style={{ width: 60 }}
          />
        </label>
        <label>
          Min Confidence
          <input
            type="number"
            min={0}
            max={100}
            value={filters.minConfidence}
            onChange={(e) => setFilters((f) => ({ ...f, minConfidence: Number(e.target.value) }))}
            style={{ width: 60 }}
          />
        </label>
        <label>
          Max KR Sellers
          <input
            type="number"
            min={0}
            placeholder="any"
            onChange={(e) =>
              setFilters((f) => ({
                ...f,
                maxKrSellers: e.target.value === "" ? undefined : Number(e.target.value),
              }))
            }
            style={{ width: 60 }}
          />
        </label>
        <label>
          Status
          <select
            onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value || undefined }))}
            defaultValue=""
          >
            <option value="">any</option>
            <option value="NEW">NEW</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="STALE">STALE</option>
            <option value="REJECTED">REJECTED</option>
          </select>
        </label>
      </div>

      {error && <p style={{ color: "var(--bad)" }}>{error}</p>}

      <table>
        <thead>
          <tr>
            <th>Product</th>
            <th onClick={() => toggleSort("opportunity_score")}>Opportunity</th>
            <th onClick={() => toggleSort("confidence_score")}>Confidence</th>
            <th>Japan Price</th>
            <th>Korea Price</th>
            <th>Expected Margin</th>
            <th>Competition</th>
            <th onClick={() => toggleSort("created_at")}>Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item: OpportunityListItem) => (
            <tr key={item.id} onClick={() => (window.location.href = `/opportunities/${item.id}`)}>
              <td>{item.product_title}</td>
              <td className={`score ${scoreClass(item.opportunity_score)}`}>{item.opportunity_score}</td>
              <td className={`score ${scoreClass(item.confidence_score)}`}>{item.confidence_score}</td>
              <td>¥{item.japan_purchase_price_jpy.toLocaleString()}</td>
              <td>₩{item.korea_sale_price_krw.toLocaleString()}</td>
              <td style={{ color: item.expected_margin_krw > 0 ? "var(--good)" : "var(--bad)" }}>
                ₩{Math.round(item.expected_margin_krw).toLocaleString()}
              </td>
              <td>{item.kr_seller_count} sellers</td>
              <td>{item.status}</td>
            </tr>
          ))}
          {items.length === 0 && !error && (
            <tr>
              <td colSpan={8} style={{ color: "var(--text-dim)" }}>
                No opportunities match these filters. Run <code>scripts/seed.sh</code> if the list is empty.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </main>
  );
}
