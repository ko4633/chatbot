"use client";

import { Fragment, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { fetchOpportunityDetail, postDecision } from "@/lib/api";
import type { OpportunityDetail } from "@/lib/types";

const DECISIONS = ["BUY_TEST", "WATCH", "REJECT", "ARCHIVE"] as const;

export default function OpportunityDetailPage() {
  const params = useParams<{ id: string }>();
  const [detail, setDetail] = useState<OpportunityDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function load() {
    fetchOpportunityDetail(params.id)
      .then(setDetail)
      .catch((e) => setError(String(e)));
  }

  useEffect(load, [params.id]);

  if (error) return <main className="container"><p style={{ color: "var(--bad)" }}>{error}</p></main>;
  if (!detail) return <main className="container"><p>Loading…</p></main>;

  const whyNow = detail.insights.find((i) => i.title === "Why Now");
  const counterArgument = detail.insights.find((i) => i.title === "Counter-Argument");

  async function submitDecision(decision: string) {
    setSubmitting(true);
    try {
      await postDecision(detail!.id, { user_email: "local-user@omnis", decision, reason });
      setReason("");
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="container">
      <a className="back-link" href="/">← Today&apos;s Intelligence</a>

      <div className="panel">
        <h2>Summary</h2>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <h3 style={{ margin: 0 }}>{detail.product_title}</h3>
          {detail.is_mock && <span className="mock-badge">MOCK DATA</span>}
          <span className="pill">{detail.status}</span>
        </div>
        <div className="kv">
          <dt>Opportunity Score</dt><dd>{detail.opportunity_score} / 100</dd>
          <dt>Confidence Score</dt><dd>{detail.confidence_score} / 100 (independent axis — see docs/AI_POLICY.md)</dd>
          <dt>Weights Version</dt><dd>{detail.weights_version}</dd>
          <dt>Regulation Status</dt><dd>{detail.regulation_status} — {detail.regulation_basis}</dd>
        </div>
      </div>

      <div className="grid-2">
        <div className="panel">
          <h2>Why Now</h2>
          <p>{whyNow?.narrative ?? "No narrative available."}</p>
          {whyNow && !whyNow.is_ai_generated && (
            <p style={{ fontSize: 11, color: "var(--text-dim)" }}>Deterministic summary (AI disabled).</p>
          )}
        </div>
        <div className="panel">
          <h2>Risks / Counter-Argument</h2>
          <p>{counterArgument?.narrative ?? "No counter-argument available."}</p>
        </div>
      </div>

      <div className="panel">
        <h2>Expected Economics</h2>
        <div className="kv">
          {Object.entries(detail.economics).map(([k, v]) => (
            <Fragment key={k}>
              <dt>{k}</dt>
              <dd>{typeof v === "number" ? v.toLocaleString() : String(v)}</dd>
            </Fragment>
          ))}
        </div>
      </div>

      <div className="panel">
        <h2>Evidence — Score Breakdown</h2>
        <table>
          <thead><tr><th>Component</th><th>Score</th><th>Weight</th><th>Contribution</th></tr></thead>
          <tbody>
            {Object.entries(detail.sub_scores.weighted_components).map(([name, c]) => (
              <tr key={name}>
                <td>{name}</td><td>{c.score}</td><td>{c.weight}</td><td>{c.contribution}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid-2">
        <div className="panel">
          <h2>Japan Market</h2>
          {detail.japan_offers.map((o) => (
            <div key={o.offer_id} style={{ marginBottom: 8, fontSize: 13 }}>
              <div>{o.title_raw}</div>
              <div style={{ color: "var(--text-dim)" }}>
                {o.seller_name} · ¥{o.latest_price?.toLocaleString()} · {o.in_stock ? "in stock" : "out of stock"}
              </div>
              <div className="source-link">{o.listing_url}</div>
            </div>
          ))}
        </div>
        <div className="panel">
          <h2>Korea Market</h2>
          {detail.korea_offers.map((o) => (
            <div key={o.offer_id} style={{ marginBottom: 8, fontSize: 13 }}>
              <div>{o.title_raw}</div>
              <div style={{ color: "var(--text-dim)" }}>
                {o.seller_name} · ₩{o.latest_price?.toLocaleString()} · {o.in_stock ? "in stock" : "out of stock"}
              </div>
              <div className="source-link">{o.listing_url}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="panel">
        <h2>Price History</h2>
        <div className="grid-2">
          <div>
            <strong>Japan</strong>
            <table><tbody>
              {detail.price_history_jp.map((p, i) => (
                <tr key={i}><td>{new Date(p.observed_at).toLocaleDateString()}</td><td>¥{p.price_amount.toLocaleString()}</td></tr>
              ))}
            </tbody></table>
          </div>
          <div>
            <strong>Korea</strong>
            <table><tbody>
              {detail.price_history_kr.map((p, i) => (
                <tr key={i}><td>{new Date(p.observed_at).toLocaleDateString()}</td><td>₩{p.price_amount.toLocaleString()}</td></tr>
              ))}
            </tbody></table>
          </div>
        </div>
        {detail.events.length > 0 && (
          <>
            <strong>Detected Events</strong>
            <ul>
              {detail.events.map((e) => (
                <li key={e.id}>{e.event_type} — {e.change_pct}% (confidence {e.confidence})</li>
              ))}
            </ul>
          </>
        )}
      </div>

      <div className="panel">
        <h2>Entity Match Evidence</h2>
        {detail.entity_matches.length === 0 && <p style={{ color: "var(--text-dim)" }}>No cross-market match recorded.</p>}
        {detail.entity_matches.map((m) => (
          <div key={m.id} style={{ marginBottom: 10 }}>
            <div>
              <span className={`pill ${m.match_type}`}>{m.match_type}</span>{" "}
              <span style={{ color: "var(--text-dim)" }}>via {m.match_stage} · confidence {m.match_confidence} · algo {m.algorithm_version}</span>
            </div>
            <div style={{ fontSize: 13, margin: "4px 0" }}>{m.left_title} ↔ {m.right_title}</div>
            <div className="evidence-json">{JSON.stringify(m.evidence, null, 2)}</div>
          </div>
        ))}
      </div>

      <div className="panel">
        <h2>AI Analysis</h2>
        <p style={{ fontSize: 13 }}>
          {detail.insights.some((i) => i.is_ai_generated)
            ? "Narrative sections above were generated by the configured AI provider."
            : "AI is disabled for this run — narrative sections above are deterministic summaries, not model output. See docs/AI_POLICY.md."}
        </p>
      </div>

      <div className="panel">
        <h2>Sources</h2>
        {detail.sources.map((s) => (
          <div key={s.id} style={{ fontSize: 13, marginBottom: 4 }}>
            {s.name} — {s.source_type} / {s.trust_tier} · reliability {s.factual_reliability} · signal {s.signal_value}
            {s.is_mock && <span className="mock-badge" style={{ marginLeft: 8 }}>MOCK</span>}
          </div>
        ))}
      </div>

      <div className="panel">
        <h2>User Decision</h2>
        <input
          placeholder="reason (optional)"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          style={{ width: "100%", padding: 6, marginBottom: 8, background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", borderRadius: 4 }}
        />
        <div className="decision-buttons">
          {DECISIONS.map((d) => (
            <button key={d} disabled={submitting} onClick={() => submitDecision(d)}>{d}</button>
          ))}
        </div>
        {detail.decisions.length > 0 && (
          <ul style={{ marginTop: 12 }}>
            {detail.decisions.map((d) => (
              <li key={d.id} style={{ fontSize: 12, color: "var(--text-dim)" }}>
                {new Date(d.created_at).toLocaleString()} — {d.decision} {d.reason ? `(${d.reason})` : ""}
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
