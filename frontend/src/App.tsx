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

type SingleBacktestPayload = {
  symbol: string;
  strategy_id: string;
  data_source: string;
  initial_cash: number;
  ending_equity: number;
  trade_count: number;
  metrics: Record<string, number | null>;
  comparison: Record<string, Record<string, number | null>>;
  equity_curve: { timestamp: string; equity: number; drawdown: number }[];
  trades: { entry_time: string; exit_time: string; quantity: number; entry_price: number; exit_price: number; pnl: number; holding_bars: number }[];
};

type WalkForwardBacktestPayload = {
  symbol: string;
  strategy_id: string;
  model_type: string | null;
  data_source: string;
  fold_count: number;
  folds: {
    fold: number;
    training_start: string;
    training_end: string;
    validation_start: string;
    validation_end: string;
    test_start: string;
    test_end: string;
    metrics: Record<string, number | null>;
  }[];
};

type BacktestPayload = SingleBacktestPayload | WalkForwardBacktestPayload;

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
  const [backtestMode, setBacktestMode] = useState("single");
  const [backtestSymbol, setBacktestSymbol] = useState("RELIANCE.NS");
  const [backtestStrategy, setBacktestStrategy] = useState("moving_average");
  const [backtestBars, setBacktestBars] = useState("120");
  const [backtestCapital, setBacktestCapital] = useState("100000");
  const [backtestCommission, setBacktestCommission] = useState("0.001");
  const [backtestSlippage, setBacktestSlippage] = useState("5");
  const [backtestSpread, setBacktestSpread] = useState("2");
  const [backtestModelType, setBacktestModelType] = useState("logistic_regression");
  const [backtestBuyThreshold, setBacktestBuyThreshold] = useState("0.65");
  const [backtestSellThreshold, setBacktestSellThreshold] = useState("0.35");
  const [backtestTrainingWindow, setBacktestTrainingWindow] = useState("60");
  const [backtestValidationWindow, setBacktestValidationWindow] = useState("20");
  const [backtestTestWindow, setBacktestTestWindow] = useState("20");
  const [backtestStepSize, setBacktestStepSize] = useState("20");
  const [backtestStart, setBacktestStart] = useState("");
  const [backtestEnd, setBacktestEnd] = useState("");
  const [backtest, setBacktest] = useState<BacktestPayload | null>(null);
  const [backtestError, setBacktestError] = useState<string | null>(null);
  const [backtestLoading, setBacktestLoading] = useState(false);

  const runBacktest = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBacktestLoading(true);
    setBacktestError(null);
    const params = new URLSearchParams({
      symbol: backtestSymbol.trim(),
      strategy_id: backtestStrategy,
      limit: backtestBars,
      initial_cash: backtestCapital,
    });
    let endpoint = "/api/backtests/run";
    if (backtestMode === "walk_forward") {
      endpoint = "/api/backtests/walk-forward";
      params.set("training_window", backtestTrainingWindow);
      params.set("validation_window", backtestValidationWindow);
      params.set("test_window", backtestTestWindow);
      params.set("step_size", backtestStepSize);
      if (backtestStrategy === "ml_probability") {
        params.set("model_type", backtestModelType);
        params.set("buy_threshold", backtestBuyThreshold);
        params.set("sell_threshold", backtestSellThreshold);
      }
    } else {
      params.set("commission_rate", backtestCommission);
      params.set("slippage_bps", backtestSlippage);
      params.set("spread_bps", backtestSpread);
      if (backtestStart) params.set("start_date", backtestStart);
      if (backtestEnd) params.set("end_date", backtestEnd);
    }
    try {
      const response = await fetch(`${API_ORIGIN}${endpoint}?${params.toString()}`);
      if (!response.ok) {
        const detail = (await response.json().catch(() => ({}))) as { detail?: string };
        throw new Error(detail.detail ?? `API returned ${response.status}`);
      }
      setBacktest((await response.json()) as BacktestPayload);
    } catch (fetchError) {
      setBacktestError(fetchError instanceof Error ? fetchError.message : "Backtest request failed");
      setBacktest(null);
    } finally {
      setBacktestLoading(false);
    }
  };

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
          <a className="nav-link" href="#backtesting"><span>⌁</span> Backtesting</a>
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
        <section className="backtesting-section" id="backtesting">
          <div className="section-heading"><div><p className="eyebrow">Historical simulation</p><h2>Backtesting</h2></div><span className="readonly-tag">RESEARCH ONLY</span></div>
          <div className="backtest-layout">
            <form className="panel backtest-form" onSubmit={runBacktest}>
              <label>Symbol<input required value={backtestSymbol} onChange={(event) => setBacktestSymbol(event.target.value)} /></label>
              <label>Evaluation<select value={backtestMode} onChange={(event) => { const mode = event.target.value; setBacktestMode(mode); if (mode === "walk_forward" && backtestStrategy === "buy_and_hold") setBacktestStrategy("moving_average"); }}><option value="single">Single historical window</option><option value="walk_forward">Chronological walk-forward</option></select></label>
              <label>Strategy<select value={backtestStrategy} onChange={(event) => setBacktestStrategy(event.target.value)}><option value="moving_average">Moving average crossover</option>{backtestMode === "single" ? <option value="buy_and_hold">Buy and hold</option> : <option value="ml_probability">ML probability</option>}</select></label>
              {backtestMode === "single" ? <div className="backtest-dates"><label>Start date<input type="date" value={backtestStart} onChange={(event) => setBacktestStart(event.target.value)} /></label><label>End date<input type="date" value={backtestEnd} onChange={(event) => setBacktestEnd(event.target.value)} /></label></div> : <div className="walk-forward-windows"><label>Training bars<input type="number" min="2" required value={backtestTrainingWindow} onChange={(event) => setBacktestTrainingWindow(event.target.value)} /></label><label>Validation bars<input type="number" min="1" required value={backtestValidationWindow} onChange={(event) => setBacktestValidationWindow(event.target.value)} /></label><label>Test bars<input type="number" min="1" required value={backtestTestWindow} onChange={(event) => setBacktestTestWindow(event.target.value)} /></label><label>Step bars<input type="number" min="1" required value={backtestStepSize} onChange={(event) => setBacktestStepSize(event.target.value)} /></label></div>}
              <label>Bars to include<input type="number" min={backtestMode === "single" ? 20 : 3} max={backtestMode === "single" ? 300 : 10000} required value={backtestBars} onChange={(event) => setBacktestBars(event.target.value)} /></label>
              {backtestMode === "walk_forward" && backtestStrategy === "ml_probability" && <>
                <label>Classifier<select value={backtestModelType} onChange={(event) => setBacktestModelType(event.target.value)}><option value="logistic_regression">Logistic Regression</option><option value="random_forest">Random Forest</option></select></label>
                <div className="backtest-dates"><label>Buy probability<input type="number" min="0.01" max="1" step="0.01" required value={backtestBuyThreshold} onChange={(event) => setBacktestBuyThreshold(event.target.value)} /></label><label>Sell probability<input type="number" min="0" max="0.99" step="0.01" required value={backtestSellThreshold} onChange={(event) => setBacktestSellThreshold(event.target.value)} /></label></div>
                <p className="research-muted">The model is refit on each training window and scored only on its later test window.</p>
              </>}
              <label>Initial capital (INR)<input type="number" min="1" step="any" required value={backtestCapital} onChange={(event) => setBacktestCapital(event.target.value)} /></label>
              {backtestMode === "single" && <div className="backtest-costs"><label>Commission rate<input type="number" min="0" max="0.999999" step="any" value={backtestCommission} onChange={(event) => setBacktestCommission(event.target.value)} /></label><label>Slippage (bps)<input type="number" min="0" step="any" value={backtestSlippage} onChange={(event) => setBacktestSlippage(event.target.value)} /></label><label>Spread (bps)<input type="number" min="0" step="any" value={backtestSpread} onChange={(event) => setBacktestSpread(event.target.value)} /></label></div>}
              {backtestError && <p className="research-error" role="alert">Backtest unavailable: {backtestError}</p>}
              <button className="refresh-button research-submit" type="submit" disabled={backtestLoading}>{backtestLoading ? "Running backtest…" : backtestMode === "walk_forward" ? "Run walk-forward evaluation" : "Run backtest"}</button>
            </form>
            <article className="panel backtest-output" aria-live="polite">
              <div className="panel-heading"><div><h3>{backtest ? `${backtest.symbol} results` : "Backtest results"}</h3><p>{backtest ? `${backtest.strategy_id.replace(/_/g, " ")} · ${backtest.data_source} data` : "Configure a run to see performance"}</p></div>{backtest && <span className="count-badge">{"folds" in backtest ? `${backtest.fold_count} folds` : `${backtest.trade_count} trades`}</span>}</div>
              {backtest ? <>
                {backtest.data_source === "synthetic" && <p className="research-disclaimer">Synthetic sample data is illustrative and does not represent actual market performance.</p>}
                {"folds" in backtest ? <>
                  <p className="research-muted">Each row reports performance on that fold’s held-out test window. Costs use the walk-forward endpoint defaults.</p>
                  {backtest.folds.length ? <div className="table-wrap"><table><thead><tr><th>Fold</th><th>Test window</th><th>Return</th><th>Sharpe</th><th>Max drawdown</th><th>Trades</th></tr></thead><tbody>{backtest.folds.map((fold) => <tr key={fold.fold}><td>{fold.fold}</td><td>{new Date(fold.test_start).toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata" })} – {new Date(fold.test_end).toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata" })}</td><td>{(((fold.metrics.total_return ?? 0) * 100)).toFixed(2)}%</td><td>{(fold.metrics.sharpe_ratio ?? 0).toFixed(2)}</td><td>{(((fold.metrics.max_drawdown ?? 0) * 100)).toFixed(2)}%</td><td>{fold.metrics.trade_count ?? 0}</td></tr>)}</tbody></table></div> : <p className="research-muted">The selected history is too short to create a complete fold.</p>}
                </> : <>
                  <div className="backtest-metrics"><BacktestMetric label="Total return" value={`${((backtest.metrics.total_return ?? 0) * 100).toFixed(2)}%`} /><BacktestMetric label="Sharpe ratio" value={(backtest.metrics.sharpe_ratio ?? 0).toFixed(2)} /><BacktestMetric label="Max drawdown" value={`${((backtest.metrics.max_drawdown ?? 0) * 100).toFixed(2)}%`} /><BacktestMetric label="Ending equity" value={formatMoney(backtest.ending_equity)} /></div>
                  <div className="backtest-comparison"><span>Strategy comparison using the same window and costs</span><strong>Moving average {( (backtest.comparison.moving_average?.total_return ?? 0) * 100).toFixed(2)}%</strong><strong>Buy &amp; hold {( (backtest.comparison.buy_and_hold?.total_return ?? 0) * 100).toFixed(2)}%</strong></div>
                  <div className="equity-chart"><svg viewBox="0 0 760 180" role="img" aria-label="Backtest equity curve"><polyline points={equityPolyline(backtest.equity_curve)} fill="none" stroke="#62d6a0" strokeWidth="2.5" vectorEffect="non-scaling-stroke" /></svg><div><span>Equity curve</span><span>{backtest.equity_curve.length} observations</span></div></div>
                  <h4>Closed trades</h4>
                  {backtest.trades.length ? (
                    <div className="table-wrap">
                      <table>
                        <thead><tr><th>Entry</th><th>Exit</th><th>Qty</th><th>Entry price</th><th>Exit price</th><th>P&amp;L</th></tr></thead>
                        <tbody>
                          {backtest.trades.slice().reverse().slice(0, 20).map((trade) => (
                            <tr key={`${trade.entry_time}-${trade.exit_time}`}>
                              <td>{new Date(trade.entry_time).toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata" })}</td>
                              <td>{new Date(trade.exit_time).toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata" })}</td>
                              <td>{trade.quantity.toLocaleString("en-IN", { maximumFractionDigits: 3 })}</td>
                              <td>{formatMoney(trade.entry_price)}</td>
                              <td>{formatMoney(trade.exit_price)}</td>
                              <td className={trade.pnl >= 0 ? "positive-text" : "negative-text"}>{formatMoney(trade.pnl)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : <p className="research-muted">No closed trades in this window.</p>}
                </>}
              </> : <EmptyState>Run a historical simulation to see metrics, equity, and trade history.</EmptyState>}
              <p className="research-footnote">Backtest fills use next-bar opens and include transaction-cost assumptions. Historical results do not predict future returns.</p>
            </article>
          </div>
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

function BacktestMetric({ label, value }: { label: string; value: string }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}

function equityPolyline(points: SingleBacktestPayload["equity_curve"]) {
  if (points.length < 2) return "";
  const values = points.map((point) => point.equity);
  const min = Math.min(...values);
  const range = Math.max(...values) - min || 1;
  return values.map((value, index) => {
    const x = (index / (values.length - 1)) * 740 + 10;
    const y = 160 - ((value - min) / range) * 140;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
}

export default App;
