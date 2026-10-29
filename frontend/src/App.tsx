import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";

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
  };
};

const API_URL = `${import.meta.env.VITE_API_URL ?? "http://localhost:8001"}/api/dashboard/overview`;
const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
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
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 30_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const portfolio = data?.portfolio;
  const performance = data?.performance ?? {};
  const execution = data?.execution ?? {};
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
        </nav>
        <div className="sidebar-note">
          <span className="status-dot" /> Paper environment
          <small>Live trading disabled</small>
        </div>
      </aside>

      <section className="content" id="overview">
        <header className="topbar">
          <div>
            <p className="eyebrow">Workspace / Overview</p>
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
          <span>{updatedAt ? `Updated ${updatedAt.toLocaleTimeString()}` : "Waiting for API"}</span>
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

        <section className="performance-strip">
          <div><span className="eyebrow">Latest performance report</span><strong>{performance.total_return == null ? "—" : `${(performance.total_return * 100).toFixed(2)}%`}</strong><small>Total return</small></div>
          <div><strong>{performance.sharpe_ratio == null ? "—" : performance.sharpe_ratio.toFixed(2)}</strong><small>Sharpe ratio</small></div>
          <div><strong>{formatMoney(performance.final_equity)}</strong><small>Reported final equity</small></div>
          <p>Performance metrics are populated by completed backtests; they do not predict future results.</p>
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
