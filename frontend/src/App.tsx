import { useEffect, useState } from "react";

type DashboardPayload = {
  status: string;
  portfolio?: {
    cash?: number;
    equity?: number;
    positions?: Record<string, number>;
  };
  performance?: {
    total_return?: number;
    sharpe_ratio?: number;
  };
  execution?: {
    open_orders?: number;
    stale_orders?: number;
  };
};

const API_URL = "http://localhost:8001/api/dashboard/overview";

function App() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(API_URL)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Request failed with ${response.status}`);
        }
        return response.json();
      })
      .then((payload) => setData(payload))
      .catch((fetchError) => setError(String(fetchError)));
  }, []);

  return (
    <main className="shell">
      <header className="header">
        <div>
          <p className="eyebrow">AI Trading Platform</p>
          <h1>Operations Dashboard</h1>
        </div>
      </header>

      {error ? (
        <section className="card error">
          Unable to load dashboard: {error}
        </section>
      ) : null}

      {!data && !error ? (
        <section className="card">Loading dashboard…</section>
      ) : null}

      {data ? (
        <section className="grid">
          <article className="card">
            <h2>Portfolio</h2>
            <dl>
              <div>
                <dt>Cash</dt>
                <dd>${(data.portfolio?.cash ?? 0).toLocaleString()}</dd>
              </div>
              <div>
                <dt>Equity</dt>
                <dd>${(data.portfolio?.equity ?? 0).toLocaleString()}</dd>
              </div>
              <div>
                <dt>Positions</dt>
                <dd>{Object.keys(data.portfolio?.positions ?? {}).length}</dd>
              </div>
            </dl>
          </article>

          <article className="card">
            <h2>Performance</h2>
            <dl>
              <div>
                <dt>Total return</dt>
                <dd>
                  {((data.performance?.total_return ?? 0) * 100).toFixed(2)}%
                </dd>
              </div>
              <div>
                <dt>Sharpe</dt>
                <dd>{(data.performance?.sharpe_ratio ?? 0).toFixed(2)}</dd>
              </div>
            </dl>
          </article>

          <article className="card">
            <h2>Execution</h2>
            <dl>
              <div>
                <dt>Open orders</dt>
                <dd>{data.execution?.open_orders ?? 0}</dd>
              </div>
              <div>
                <dt>Stale orders</dt>
                <dd>{data.execution?.stale_orders ?? 0}</dd>
              </div>
            </dl>
          </article>
        </section>
      ) : null}
    </main>
  );
}

export default App;
