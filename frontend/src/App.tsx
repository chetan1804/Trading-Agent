import { useCallback, useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";

type DashboardPayload = {
  status: string;
  portfolio?: {
    cash?: number;
    positions?: Record<string, number>;
    last_prices?: Record<string, number>;
    realized_pnl?: number;
    unrealized_pnl?: number;
    net_pnl?: number;
    total_value?: number;
    exposure?: number;
  };
  performance?: Record<string, number>;
  execution?: {
    open_orders?: number;
    filled_orders?: number;
    stale_orders?: number;
    avg_fill_slippage_bps?: Record<string, number>;
    recent_fills?: {
      order_id: string;
      symbol: string;
      side: string;
      status: string;
      filled_quantity: number;
      avg_fill_price: number;
      order_submitted_at: string;
    }[];
  };
  risk?: {
    status: string;
    new_exposure_allowed: boolean;
    daily_pnl: number;
    daily_pnl_basis: string;
    daily_loss_fraction: number;
    max_daily_loss_fraction: number;
    drawdown_fraction: number;
    max_drawdown_fraction: number;
    exposure: number;
    exposure_fraction: number;
    max_portfolio_exposure_fraction: number;
    open_positions: number;
    max_open_positions: number;
    reasons: string[];
  };
};

type ResearchReport = {
  symbol: string;
  provider: string;
  summary: string;
  risks: string[];
  highlights: string[];
};

type AgentReport = {
  symbol: string;
  status: string;
  objective: string;
  plan: string[];
  actions: string[];
  sentiment: { sentiment: string; score: number; headline_count: number };
  research_context: { answer: string; citations: string[]; sources: { source_id: string; excerpt: string; relevance_score: number }[] };
  risks_and_uncertainties: string[];
};

type MonitoringPayload = {
  status: string;
  alerts: string[];
  model?: {
    status?: string;
    reason?: string;
    model_version?: string;
    observation_count?: number;
    labeled_count?: number;
    accuracy?: number | null;
    feature_drift?: Record<string, number> | null;
  };
};

const API_ORIGIN = import.meta.env.VITE_API_URL ?? "http://localhost:8001";
const API_URL = `${API_ORIGIN}/api/dashboard/overview`;
const money = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 2,
});

function formatMoney(value?: number) {
  return money.format(value ?? 0);
}

function App() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [loading, setLoading] = useState(true);
  const [researchSymbol, setResearchSymbol] = useState("RELIANCE.NS");
  const [researchPrice, setResearchPrice] = useState("");
  const [researchChange, setResearchChange] = useState("");
  const [researchVolume, setResearchVolume] = useState("");
  const [researchNews, setResearchNews] = useState("");
  const [researchDocuments, setResearchDocuments] = useState("");
  const [research, setResearch] = useState<ResearchReport | null>(null);
  const [researchError, setResearchError] = useState<string | null>(null);
  const [researchLoading, setResearchLoading] = useState(false);
  const [agentObjective, setAgentObjective] = useState("Assess the recent market context and summarize key risks.");
  const [agentReport, setAgentReport] = useState<AgentReport | null>(null);
  const [agentError, setAgentError] = useState<string | null>(null);
  const [agentLoading, setAgentLoading] = useState(false);
  const [monitoring, setMonitoring] = useState<MonitoringPayload | null>(null);
  const [monitoringError, setMonitoringError] = useState<string | null>(null);

  const agentPayload = () => ({
    symbol: researchSymbol.trim(),
    objective: agentObjective.trim(),
    market_snapshot: {
      ...(researchPrice ? { price: Number(researchPrice) } : {}),
      ...(researchChange ? { change_pct: Number(researchChange) } : {}),
      ...(researchVolume ? { volume: Number(researchVolume) } : {}),
    },
    news: researchNews.split("\n").map((item) => item.trim()).filter(Boolean),
    documents: researchDocuments.split("\n").map((item) => item.trim()).filter(Boolean),
  });

  const runAgent = async () => {
    setAgentLoading(true);
    setAgentError(null);
    try {
      const response = await fetch(`${API_ORIGIN}/api/agents/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(agentPayload()),
      });
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      setAgentReport((await response.json()) as AgentReport);
    } catch (fetchError) {
      setAgentError(fetchError instanceof Error ? fetchError.message : "Agent request failed");
      setAgentReport(null);
    } finally {
      setAgentLoading(false);
    }
  };

  const runResearch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setResearchLoading(true);
    setResearchError(null);
    try {
      const response = await fetch(`${API_ORIGIN}/api/ai/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: researchSymbol.trim(),
          market_snapshot: {
            ...(researchPrice ? { price: Number(researchPrice) } : {}),
            ...(researchChange ? { change_pct: Number(researchChange) } : {}),
            ...(researchVolume ? { volume: Number(researchVolume) } : {}),
          },
          news: researchNews.split("\n").map((item) => item.trim()).filter(Boolean),
          documents: researchDocuments.split("\n").map((item) => item.trim()).filter(Boolean),
        }),
      });
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      setResearch((await response.json()) as ResearchReport);
    } catch (fetchError) {
      setResearchError(fetchError instanceof Error ? fetchError.message : "Research request failed");
      setResearch(null);
    } finally {
      setResearchLoading(false);
    }
  };

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(API_URL);
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      setData((await response.json()) as DashboardPayload);
      setError(null);
      setUpdatedAt(new Date());
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Request failed");
    } finally {
      setLoading(false);
    }
    try {
      const response = await fetch(`${API_ORIGIN}/api/monitoring/overview`);
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      setMonitoring((await response.json()) as MonitoringPayload);
      setMonitoringError(null);
    } catch (fetchError) {
      setMonitoringError(fetchError instanceof Error ? fetchError.message : "Request failed");
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 30_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const portfolio = data?.portfolio;
  const performance = data?.performance ?? {};
  const execution = data?.execution ?? {};
  const risk = data?.risk;
  const positions = Object.entries(portfolio?.positions ?? {});
  const prices = portfolio?.last_prices ?? {};

  return (
    <main className="shell">
      <aside className="sidebar">
        <a className="brand" href="#overview" aria-label="Trading platform home">
          <span className="brand-mark">T</span>
          <span>Northstar<span className="brand-subtitle">Trading systems</span></span>
        </a>
        <nav aria-label="Main navigation">
          <a className="nav-link active" href="#overview"><span>◫</span> Overview</a>
          <a className="nav-link" href="#portfolio"><span>▤</span> Portfolio</a>
          <a className="nav-link" href="#execution"><span>⇄</span> Execution</a>
          <a className="nav-link" href="#research"><span>⌕</span> AI Research</a>
        </nav>
        <div className="sidebar-note">
          <span className="status-dot" /> Paper environment
          <small>Live trading disabled</small>
        </div>
      </aside>

      <section className="content" id="overview">
        <header className="topbar">
          <div>
            <p className="eyebrow">Indian markets / Overview</p>
            <h1>Operations</h1>
          </div>
          <div className="topbar-actions">
            <span className="environment"><span className="status-dot" /> PAPER</span>
            <button className="refresh-button" onClick={() => void refresh()} disabled={loading}>
              <span aria-hidden="true">↻</span> {loading ? "Updating" : "Refresh"}
            </button>
          </div>
        </header>

        <div className="snapshot-line">
          <span>Account snapshot</span>
          <span>{updatedAt ? `Updated ${updatedAt.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata" })} IST` : "Waiting for API"}</span>
        </div>

        {error && (
          <section className="notice" role="alert">
            <div><strong>Dashboard data unavailable</strong><p>{error}. Check that the API is running at {API_URL.replace("/api/dashboard/overview", "")}.</p></div>
            <button onClick={() => void refresh()}>Retry</button>
          </section>
        )}

        <section className="metric-grid" aria-label="Account summary">
          <Metric label="Total account value" value={formatMoney(portfolio?.total_value)} note="Cash and marked positions" />
          <Metric label="Available cash" value={formatMoney(portfolio?.cash)} note="Ready for paper orders" />
          <Metric label="Net P&L" value={formatMoney(portfolio?.net_pnl)} note={`${formatMoney(portfolio?.realized_pnl)} realized`} tone={(portfolio?.net_pnl ?? 0) >= 0 ? "positive" : "negative"} />
          <Metric label="Market exposure" value={formatMoney(portfolio?.exposure)} note={`${positions.length} open positions`} />
        </section>

        <div className="section-heading"><div><p className="eyebrow">Account activity</p><h2>Portfolio & execution</h2></div><span className="readonly-tag">READ ONLY</span></div>
        <section className="panel-grid">
          <article className="panel" id="portfolio">
            <div className="panel-heading"><div><h3>Open positions</h3><p>Current paper account holdings</p></div><span className="count-badge">{positions.length}</span></div>
            {positions.length ? (
              <div className="table-wrap"><table><thead><tr><th>Symbol</th><th>Quantity</th><th>Last price</th><th>Market value</th></tr></thead><tbody>
                {positions.map(([symbol, quantity]) => <tr key={symbol}><td className="symbol">{symbol}</td><td>{quantity.toLocaleString()}</td><td>{formatMoney(prices[symbol])}</td><td>{formatMoney(quantity * (prices[symbol] ?? 0))}</td></tr>)}
              </tbody></table></div>
            ) : <EmptyState>There are no open positions in this paper account.</EmptyState>}
          </article>

          <article className="panel" id="execution">
            <div className="panel-heading"><div><h3>Execution health</h3><p>Paper order lifecycle</p></div><span className="health-pill"><span className="status-dot" /> {data?.status === "ok" ? "Operational" : "Connecting"}</span></div>
            <div className="execution-stats">
              <div><span>Open orders</span><strong>{execution.open_orders ?? 0}</strong></div>
              <div><span>Filled orders</span><strong>{execution.filled_orders ?? 0}</strong></div>
              <div><span>Stale orders</span><strong className={(execution.stale_orders ?? 0) > 0 ? "negative-text" : ""}>{execution.stale_orders ?? 0}</strong></div>
            </div>
            <div className="panel-footer">Orders require explicit risk approval and a separate fill action.</div>
          </article>
        </section>

        <article className="panel recent-fills-panel">
          <div className="panel-heading"><div><h3>Recent paper fills</h3><p>Order submission time shown in IST</p></div><span className="count-badge">{execution.recent_fills?.length ?? 0}</span></div>
          {execution.recent_fills?.length ? <div className="table-wrap"><table><thead><tr><th>Submitted</th><th>Symbol</th><th>Side</th><th>Status</th><th>Filled qty</th><th>Average fill</th></tr></thead><tbody>
            {execution.recent_fills.map((fill) => <tr key={fill.order_id}><td>{new Date(fill.order_submitted_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", dateStyle: "medium", timeStyle: "short" })}</td><td className="symbol">{fill.symbol}</td><td>{fill.side}</td><td>{fill.status}</td><td>{fill.filled_quantity.toLocaleString("en-IN")}</td><td>{formatMoney(fill.avg_fill_price)}</td></tr>)}
          </tbody></table></div> : <EmptyState>No paper fills have been recorded.</EmptyState>}
        </article>

        <section className="performance-strip">
          <div><span className="eyebrow">Latest performance report</span><strong>{performance.total_return == null ? "—" : `${(performance.total_return * 100).toFixed(2)}%`}</strong><small>Total return</small></div>
          <div><strong>{performance.sharpe_ratio == null ? "—" : performance.sharpe_ratio.toFixed(2)}</strong><small>Sharpe ratio</small></div>
          <div><strong>{formatMoney(performance.final_equity)}</strong><small>Reported final equity</small></div>
          <p>Performance metrics are populated by completed backtests; they do not predict future results.</p>
        </section>
        <section className="risk-panel panel" aria-live="polite">
          <div className="panel-heading"><div><p className="eyebrow">Exposure controls</p><h3>Risk status</h3></div><span className={`monitoring-status ${risk?.status ?? "unavailable"}`}>{risk?.status ?? "unavailable"}</span></div>
          {risk ? <>
            <div className="risk-summary-line"><strong>{risk.new_exposure_allowed ? "New exposure is enabled" : "New exposure is blocked"}</strong><span>{risk.new_exposure_allowed ? "All reported checks are within limits" : risk.status === "disabled" ? "Trading kill switch is off" : "One or more risk limits are reached"}</span></div>
            <div className="monitoring-metrics">
              <div><span>Daily realized P&amp;L</span><strong className={risk.daily_pnl >= 0 ? "positive-text" : "negative-text"}>{formatMoney(risk.daily_pnl)}</strong></div>
              <div><span>Daily loss limit used</span><strong>{(risk.daily_loss_fraction * 100).toFixed(1)}% / {(risk.max_daily_loss_fraction * 100).toFixed(1)}%</strong></div>
              <div><span>Drawdown</span><strong>{(risk.drawdown_fraction * 100).toFixed(1)}% / {(risk.max_drawdown_fraction * 100).toFixed(1)}%</strong></div>
              <div><span>Exposure</span><strong>{formatMoney(risk.exposure)} · {(risk.exposure_fraction * 100).toFixed(1)}% / {(risk.max_portfolio_exposure_fraction * 100).toFixed(1)}%</strong></div>
              <div><span>Open positions</span><strong>{risk.open_positions} / {risk.max_open_positions}</strong></div>
            </div>
            {risk.reasons.length > 0 && <ul className="risk-reasons">{risk.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>}
            <p className="research-muted">Daily loss uses realized P&amp;L recorded by the paper broker. This panel reports configured pre-trade limits; it does not predict portfolio losses.</p>
          </> : <p className="research-muted">Risk status is unavailable.</p>}
        </section>
        <section className="monitoring-panel panel" aria-live="polite">
          <div className="panel-heading"><div><p className="eyebrow">Observability</p><h3>Model monitoring & alerts</h3></div><span className={`monitoring-status ${monitoring?.model?.status ?? "unavailable"}`}>{monitoring?.model?.status ?? "unavailable"}</span></div>
          {monitoringError ? <p className="research-error">Monitoring data unavailable: {monitoringError}</p> : <>
            <div className="monitoring-metrics">
              <div><span>Model version</span><strong>{monitoring?.model?.model_version ?? "—"}</strong></div>
              <div><span>Predictions observed</span><strong>{monitoring?.model?.observation_count ?? 0}</strong></div>
              <div><span>Outcomes labeled</span><strong>{monitoring?.model?.labeled_count ?? 0}</strong></div>
              <div><span>Observed accuracy</span><strong>{monitoring?.model?.accuracy == null ? "—" : `${(monitoring.model.accuracy * 100).toFixed(1)}%`}</strong></div>
            </div>
            <p className="research-muted">{monitoring?.model?.reason ?? "Metrics use recorded prediction outcomes; collection status reflects available observations."}</p>
            <h4>Active alerts</h4>
            {monitoring?.alerts.length ? <ul>{monitoring.alerts.map((alert) => <li key={alert}>{alert}</li>)}</ul> : <p className="research-muted">No monitoring response yet.</p>}
          </>}
        </section>
        <section className="research-section" id="research">
          <div className="section-heading"><div><p className="eyebrow">Structured inputs only</p><h2>Market research</h2></div><span className="readonly-tag">NON-TRADING</span></div>
          <div className="research-grid">
            <form className="panel research-form" onSubmit={runResearch}>
              <p className="research-disclaimer">Provide the market snapshot and source text to summarize. This local assistant does not fetch market data or place trades.</p>
              <label>Symbol<input required value={researchSymbol} onChange={(event) => setResearchSymbol(event.target.value)} /></label>
              <div className="research-numbers">
                <label>Price (INR)<input type="number" min="0" step="any" value={researchPrice} onChange={(event) => setResearchPrice(event.target.value)} /></label>
                <label>Change (%)<input type="number" step="any" value={researchChange} onChange={(event) => setResearchChange(event.target.value)} /></label>
                <label>Volume<input type="number" min="0" step="any" value={researchVolume} onChange={(event) => setResearchVolume(event.target.value)} /></label>
              </div>
              <label>Headlines<textarea rows={3} value={researchNews} onChange={(event) => setResearchNews(event.target.value)} placeholder="One headline per line" /></label>
              <label>Research documents<textarea rows={3} value={researchDocuments} onChange={(event) => setResearchDocuments(event.target.value)} placeholder="One source excerpt per line" /></label>
              <label>Research question<textarea rows={2} value={agentObjective} onChange={(event) => setAgentObjective(event.target.value)} /></label>
              {researchError && <p className="research-error" role="alert">Research unavailable: {researchError}</p>}
              <button className="refresh-button research-submit" type="submit" disabled={researchLoading}>{researchLoading ? "Preparing summary…" : "Generate summary"}</button>
              {agentError && <p className="research-error" role="alert">Agent unavailable: {agentError}</p>}
              <button className="refresh-button research-submit" type="button" onClick={() => void runAgent()} disabled={agentLoading || !researchSymbol.trim() || !agentObjective.trim()}>{agentLoading ? "Reviewing inputs…" : "Run research agent"}</button>
            </form>
            <article className="panel research-result" aria-live="polite">
              <div className="panel-heading"><div><h3>{research ? `${research.symbol} research brief` : "Research brief"}</h3><p>Generated from the inputs supplied</p></div>{research && <span className="count-badge">{research.provider}</span>}</div>
              {research ? <>
                <p className="research-summary">{research.summary}</p>
                <h4>Highlights</h4><ul>{research.highlights.map((item) => <li key={item}>{item}</li>)}</ul>
                <h4>Risks and uncertainty</h4><ul>{research.risks.map((item) => <li key={item}>{item}</li>)}</ul>
              </> : <EmptyState>Enter a symbol and optional context to create a research brief.</EmptyState>}
              <p className="research-footnote">Rule-based local interpretation of user-provided data, not an LLM response. Verify source facts independently; this is not a trading instruction.</p>
            </article>
          </div>
          <article className="panel agent-result" aria-live="polite">
            <div className="panel-heading"><div><h3>{agentReport ? `${agentReport.symbol} research workflow` : "Research agent"}</h3><p>Deterministic workflow using only the inputs above</p></div>{agentReport && <span className="count-badge">{agentReport.sentiment.sentiment} sentiment</span>}</div>
            {agentReport ? <div className="agent-result-grid">
              <section><h4>Review plan</h4><ul>{agentReport.plan.map((item) => <li key={item}>{item}</li>)}</ul><h4>Checks</h4><ul>{agentReport.actions.map((item) => <li key={item}>{item}</li>)}</ul></section>
              <section><h4>Retrieved research</h4>{agentReport.research_context.sources.length ? <ul>{agentReport.research_context.sources.map((source) => <li key={source.source_id}><strong>[{source.source_id}]</strong> {source.excerpt}</li>)}</ul> : <p className="research-muted">{agentReport.research_context.answer}</p>}<h4>Risks and data gaps</h4><ul>{agentReport.risks_and_uncertainties.map((item) => <li key={item}>{item}</li>)}</ul></section>
            </div> : <EmptyState>Ask a question above to run the research workflow.</EmptyState>}
            <p className="research-footnote">This workflow does not fetch or verify data, call an LLM, or approve or submit an order.</p>
          </article>
        </section>
        <footer>Research and paper-trading workspace <span>•</span> No live orders are enabled</footer>
      </section>
    </main>
  );
}

function Metric({ label, value, note, tone }: { label: string; value: string; note: string; tone?: "positive" | "negative" }) {
  return <article className="metric-card"><span>{label}</span><strong className={tone ? `${tone}-text` : ""}>{value}</strong><small>{note}</small></article>;
}

function EmptyState({ children }: { children: ReactNode }) {
  return <div className="empty-state"><span aria-hidden="true">◌</span><p>{children}</p></div>;
}

export default App;
