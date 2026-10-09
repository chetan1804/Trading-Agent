# AI Automated Trading Platform — Master Project Prompt

## ROLE

You are a senior Python engineer, quantitative developer, ML engineer, MLOps engineer, and software architect.

Build a production-quality **AI Automated Trading Platform** from scratch.

The goal is to create a portfolio-quality system that can ingest market data, engineer features, generate trading signals using rule-based and ML models, backtest strategies realistically, apply strict risk management, support paper trading, monitor performance, and provide an optional AI/LLM layer for market research and explanation.

IMPORTANT:
- This project is for engineering, research, education, and paper-trading purposes.
- Do NOT promise profits or claim that any strategy is guaranteed to work.
- Default mode MUST be backtesting/paper trading.
- Live trading must be disabled by default and require an explicit configuration flag.
- Never bypass broker risk controls, exchange rules, authentication, or regulatory requirements.
- Never hard-code API keys, secrets, credentials, or private tokens.
- Clearly separate research/backtesting code from execution code.

---

# 1. PROJECT OBJECTIVE

Build an end-to-end AI-powered automated trading platform with this flow:

Market Data
    ↓
Data Validation
    ↓
Data Storage
    ↓
Feature Engineering
    ↓
Strategy / ML Model
    ↓
Signal Generation
    ↓
Risk Management
    ↓
Portfolio / Position Management
    ↓
Order Management
    ↓
Paper Broker / Optional Broker Adapter
    ↓
Execution Tracking
    ↓
Monitoring
    ↓
Performance Analytics
    ↓
AI/LLM Research & Explanation

The system should be modular so that individual components can be replaced without rewriting the entire application.

---

# 2. PRIMARY GOALS

The system must support:

1. Historical market-data ingestion
2. Data validation and cleaning
3. Technical indicator calculation
4. Feature engineering
5. Rule-based strategies
6. Machine-learning-based signal generation
7. Backtesting
8. Walk-forward validation
9. Risk management
10. Portfolio management
11. Paper trading
12. Broker API abstraction
13. Real-time market-data ingestion architecture
14. Order lifecycle management
15. Performance analytics
16. Model monitoring
17. Strategy monitoring
18. Logging and audit trails
19. REST APIs
20. Dashboard
21. AI/LLM-powered market research
22. News/sentiment analysis
23. RAG-based research over financial documents
24. Agentic workflows for research and analysis
25. Dockerized deployment
26. Automated tests
27. CI/CD-ready repository

---

# 3. RECOMMENDED TECH STACK

Use the following stack unless there is a strong technical reason to replace a component.

## Backend

- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis
- Celery or an equivalent background-job system

## Data / ML

- Pandas
- NumPy
- scikit-learn
- XGBoost
- joblib
- scipy where useful

## Technical Analysis

Prefer a well-maintained Python technical-analysis library where practical.

Indicators can include:

- SMA
- EMA
- RSI
- MACD
- Bollinger Bands
- ATR
- ADX
- Stochastic Oscillator
- OBV
- VWAP
- returns
- volatility
- rolling statistics

## AI / GenAI

Use modular adapters for:

- OpenAI
- Mistral
- Groq
- Ollama/local models

Use LangChain/LangGraph only where they add real value.

Possible AI features:

- financial-news summarization
- sentiment analysis
- market research assistant
- document Q&A
- RAG
- strategy explanation
- portfolio explanation
- agentic research workflow

Do NOT use an LLM as the sole source of a trading decision.

## Frontend

Use:

- React
- TypeScript
- Vite
- a clean component library
- responsive charts

The frontend should communicate with FastAPI.

## Database

PostgreSQL.

Use Redis for:

- caching
- task queues
- temporary state
- real-time coordination where appropriate

## Deployment

- Docker
- Docker Compose
- GitHub Actions
- AWS-ready architecture

Keep the system deployable on a small cloud instance for development/testing.

---

# 4. REPOSITORY STRUCTURE

Create a clean repository similar to:

ai-automated-trading/
│
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── pyproject.toml
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   │
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── health.py
│   │   │   │   ├── market_data.py
│   │   │   │   ├── strategies.py
│   │   │   │   ├── backtests.py
│   │   │   │   ├── portfolios.py
│   │   │   │   ├── orders.py
│   │   │   │   ├── performance.py
│   │   │   │   └── ai.py
│   │   │   └── dependencies.py
│   │   │
│   │   ├── core/
│   │   │   ├── logging.py
│   │   │   ├── security.py
│   │   │   └── exceptions.py
│   │   │
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── integrations/
│   │
│   └── tests/
│
├── trading/
│   ├── data/
│   │   ├── ingestion/
│   │   ├── validation/
│   │   └── providers/
│   │
│   ├── features/
│   │   ├── technical.py
│   │   ├── statistical.py
│   │   └── feature_pipeline.py
│   │
│   ├── strategies/
│   │   ├── base.py
│   │   ├── moving_average.py
│   │   ├── rsi.py
│   │   ├── momentum.py
│   │   └── ml_strategy.py
│   │
│   ├── models/
│   │   ├── base.py
│   │   ├── train.py
│   │   ├── predict.py
│   │   ├── evaluate.py
│   │   └── registry.py
│   │
│   ├── backtesting/
│   │   ├── engine.py
│   │   ├── portfolio.py
│   │   ├── execution.py
│   │   ├── costs.py
│   │   └── metrics.py
│   │
│   ├── risk/
│   │   ├── manager.py
│   │   ├── position_sizing.py
│   │   ├── stop_loss.py
│   │   └── limits.py
│   │
│   ├── execution/
│   │   ├── broker.py
│   │   ├── paper_broker.py
│   │   └── live_broker.py
│   │
│   └── portfolio/
│       ├── manager.py
│       └── analytics.py
│
├── ai/
│   ├── llm/
│   ├── agents/
│   ├── rag/
│   ├── sentiment/
│   └── prompts/
│
├── frontend/
│   └── ...
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── models/
│
├── notebooks/
│
├── scripts/
│
├── migrations/
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── backtesting.md
│   ├── risk_management.md
│   ├── ml_pipeline.md
│   └── deployment.md
│
└── .github/
    └── workflows/
        └── ci.yml

Adjust the structure if necessary, but maintain clear separation of concerns.

---

# 5. CONFIGURATION

Create a robust configuration system.

Use environment variables.

Example:

APP_ENV=development
LOG_LEVEL=INFO

DATABASE_URL=postgresql://...
REDIS_URL=redis://...

LLM_PROVIDER=ollama
LLM_MODEL=...

OPENAI_API_KEY=
MISTRAL_API_KEY=
GROQ_API_KEY=

MARKET_DATA_PROVIDER=
MARKET_DATA_API_KEY=

BROKER_MODE=paper
ENABLE_LIVE_TRADING=false

MAX_POSITION_SIZE=
MAX_DAILY_LOSS=
MAX_DRAWDOWN=
RISK_PER_TRADE=

Never commit real secrets.

Create:

.env.example

with safe placeholder values.

---

# 6. MARKET DATA LAYER

Build a provider abstraction.

Example interface:

MarketDataProvider

Methods:

- get_historical_data()
- get_latest_price()
- get_quote()
- subscribe_market_data()

Do not tightly couple the system to one vendor.

Start with a mock/local CSV provider so the entire system works without external APIs.

Then add an optional external provider adapter.

The system should normalize incoming data into a common schema.

Suggested fields:

- timestamp
- symbol
- open
- high
- low
- close
- volume

Optional:

- adjusted_close
- bid
- ask
- trade_count

---

# 7. DATA QUALITY

Implement:

- missing timestamp detection
- duplicate detection
- invalid OHLC detection
- missing-value handling
- timezone normalization
- chronological sorting
- outlier detection
- data-gap reporting

Never silently modify financial data.

Log all data-quality problems.

---

# 8. DATABASE DESIGN

Create tables/entities for at least:

users
symbols
market_data
features
strategies
strategy_runs
models
backtests
backtest_trades
portfolios
positions
orders
executions
risk_events
daily_metrics
news
sentiment_scores
ai_analysis
audit_logs

Add appropriate indexes.

Use UTC timestamps internally.

Use migrations through Alembic.

---

# 9. FEATURE ENGINEERING

Build a reusable feature pipeline.

Include:

Price Features:
- returns
- log returns
- price changes
- rolling returns

Trend Features:
- SMA
- EMA
- moving-average distance
- trend direction

Momentum:
- RSI
- MACD
- ROC
- stochastic

Volatility:
- ATR
- rolling standard deviation
- Bollinger Band width

Volume:
- volume change
- volume moving average
- OBV

Time:
- hour
- day of week
- month

Ensure no future information leaks into features.

This is critical.

---

# 10. MACHINE LEARNING

Implement a baseline ML pipeline.

Start with:

1. Logistic Regression
2. Random Forest
3. XGBoost

The model should predict something explicitly defined, such as:

- next-period direction
- probability of positive return
- probability that return exceeds a threshold

Do not train using future information.

Use chronological train/validation/test splits.

Do NOT randomly shuffle time-series data.

Implement:

- training pipeline
- validation
- evaluation
- model serialization
- model versioning
- model metadata
- prediction service

Save:

- training date
- dataset version
- feature list
- hyperparameters
- validation metrics
- model version

---

# 11. AVOID DATA LEAKAGE

This requirement is mandatory.

Check for:

- future candles leaking into features
- future returns used in current features
- random train/test splitting
- normalization fitted on test data
- target leakage
- look-ahead bias
- survivorship bias where applicable

Add automated tests for leakage-prone transformations.

---

# 12. STRATEGY ENGINE

Create a common Strategy interface.

Example:

class Strategy:
    def generate_signal(self, market_data, features):
        ...

Return a structured signal:

- symbol
- timestamp
- action: BUY / SELL / HOLD
- confidence
- reason
- strategy_id

Implement baseline strategies.

## Strategy 1: Moving Average Crossover

Example:

fast SMA crosses above slow SMA → BUY signal

fast SMA crosses below slow SMA → SELL signal

## Strategy 2: RSI

Use configurable thresholds.

## Strategy 3: Momentum

Use configurable momentum and trend features.

## Strategy 4: ML Strategy

Use model probability plus configurable threshold.

Never execute a signal directly.

Every signal must pass through risk management.

---

# 13. SIGNAL ENGINE

Create a centralized signal engine.

Responsibilities:

- receive strategy signals
- combine signals
- apply confidence thresholds
- detect conflicting signals
- check market conditions
- send candidate trades to risk management

Example:

Signal:
BUY

Confidence:
0.72

Then:

Risk Manager
    ↓
Approved / Rejected

Store every decision.

---

# 14. RISK MANAGEMENT

This is one of the most important components.

Implement configurable controls.

## Per-trade risk

Example:

risk_per_trade = 1%

Do not hard-code the value.

## Position limits

Maximum:

- position size
- portfolio exposure
- number of open positions
- symbol exposure

## Daily loss limit

If daily loss exceeds the configured threshold:

STOP NEW TRADES.

## Maximum drawdown

If portfolio drawdown exceeds the configured threshold:

PAUSE STRATEGY.

## Stop loss

Support configurable stop-loss logic.

## Take profit

Optional.

## Cooldown

Prevent repeated orders for the same symbol within a configurable time window.

## Kill switch

Implement:

ENABLE_TRADING=false

When disabled:

- no new orders
- existing positions can still be monitored
- system remains observable

---

# 15. POSITION SIZING

Implement a position-sizing service.

Inputs may include:

- account equity
- entry price
- stop-loss price
- risk percentage
- volatility
- max position size

Return:

- quantity
- capital required
- estimated risk

Always enforce hard risk limits.

---

# 16. BACKTESTING ENGINE

Build a realistic event-driven backtesting engine.

It must support:

- historical candles
- strategy signals
- position management
- order simulation
- transaction costs
- slippage
- stop loss
- take profit
- portfolio accounting

Do NOT assume every order executes at the ideal price.

Support configurable:

- commission
- slippage
- spread
- latency approximation

---

# 17. BACKTEST METRICS

Calculate:

- total return
- CAGR where applicable
- Sharpe ratio
- Sortino ratio
- maximum drawdown
- Calmar ratio
- win rate
- loss rate
- profit factor
- average win
- average loss
- expectancy
- number of trades
- average holding period
- exposure
- turnover

Also produce:

- equity curve
- drawdown curve
- monthly returns
- trade distribution

Do not use only accuracy to evaluate a trading strategy.

A model can have high classification accuracy and still lose money.

---

# 18. WALK-FORWARD VALIDATION

Implement a walk-forward framework.

Example:

Training Window
    ↓
Validation Window
    ↓
Test Window
    ↓
Move Window Forward
    ↓
Repeat

Prevent information leakage between periods.

Report performance for each period.

---

# 19. PAPER TRADING

Create a PaperBroker implementing the same interface as a real broker.

Paper broker must simulate:

- order placement
- fills
- fees
- slippage
- positions
- cash balance
- P&L
- order status

The rest of the application should not know whether it is using a paper broker or another broker implementation.

---

# 20. LIVE BROKER ABSTRACTION

Create:

Broker

with methods such as:

- place_order()
- cancel_order()
- get_order()
- get_positions()
- get_balance()
- get_open_orders()

Initially implement only a safe mock/paper broker.

If a real broker adapter is added later:

- keep credentials in environment variables
- require explicit live-trading enablement
- implement connection health checks
- validate order quantities
- validate symbols
- enforce risk limits before submission
- log every request and response safely
- never log secrets

---

# 21. ORDER MANAGEMENT SYSTEM

Implement order states:

NEW
VALIDATED
SUBMITTED
PARTIALLY_FILLED
FILLED
CANCEL_REQUESTED
CANCELLED
REJECTED
FAILED

Track:

- order ID
- strategy ID
- symbol
- side
- quantity
- order type
- limit price
- stop price
- timestamps
- broker response
- fill information

Make order handling idempotent.

---

# 22. PORTFOLIO MANAGEMENT

Track:

- cash
- equity
- positions
- unrealized P&L
- realized P&L
- exposure
- daily P&L
- drawdown

Implement portfolio-level risk checks.

---

# 23. AI / LLM LAYER

The LLM layer should NOT directly place trades.

Use AI for:

- market research
- news summarization
- sentiment analysis
- strategy explanation
- portfolio explanation
- anomaly explanation
- financial document Q&A

Example:

User asks:

"Why did the strategy generate this BUY signal?"

The AI system should explain:

- relevant indicators
- model probability
- recent market conditions
- risk checks
- strategy rules

The explanation must be based on structured system data.

Do not allow the LLM to invent trades, prices, or performance.

---

# 24. NEWS SENTIMENT

Build an optional news pipeline.

Flow:

News Source
    ↓
Deduplication
    ↓
Text Cleaning
    ↓
Sentiment Model / LLM
    ↓
Sentiment Score
    ↓
Symbol Mapping
    ↓
Database

Store:

- headline
- source
- published_at
- symbol
- sentiment
- confidence
- summary

Clearly distinguish factual market data from AI-generated interpretation.

---

# 25. RAG FOR FINANCIAL RESEARCH

Create an optional RAG system for trusted documents.

Potential documents:

- company reports
- annual reports
- earnings documents
- official filings
- strategy documentation
- research notes

Pipeline:

Documents
    ↓
Parsing
    ↓
Chunking
    ↓
Embeddings
    ↓
Vector Database
    ↓
Retriever
    ↓
LLM
    ↓
Cited Answer

The system should provide source references for retrieved information.

Do not fabricate citations.

---

# 26. AGENTIC AI

Create an optional research agent using LangGraph.

Possible workflow:

User Question
    ↓
Research Agent
    ↓
Market Data Tool
    ↓
News Tool
    ↓
RAG Tool
    ↓
Technical Analysis Tool
    ↓
Risk Analysis Tool
    ↓
Summary Agent
    ↓
Final Explanation

Example user question:

"Analyze this symbol based on recent price movement, technical indicators, and available research documents."

The agent should return:

- data used
- indicators
- observations
- risks
- uncertainties
- sources
- final non-binding analysis

The agent must NOT autonomously place a real-money trade.

---

# 27. API DESIGN

Create FastAPI endpoints.

Examples:

GET /health

GET /symbols

GET /market-data/{symbol}

POST /market-data/import

GET /strategies

POST /strategies/{id}/run

POST /backtests

GET /backtests/{id}

GET /backtests/{id}/metrics

GET /portfolio

GET /positions

GET /orders

POST /orders/paper

GET /performance

GET /risk/status

POST /risk/kill-switch

GET /models

POST /models/train

POST /models/predict

POST /ai/analyze

POST /ai/research

Use:

- Pydantic schemas
- validation
- proper HTTP status codes
- authentication-ready design
- structured error responses

---

# 28. DASHBOARD

Create a React dashboard.

Pages:

## Dashboard

Show:

- account equity
- daily P&L
- total P&L
- drawdown
- active positions
- recent trades
- risk status

## Market

Show:

- symbol
- latest price
- indicators
- chart

## Strategies

Show:

- strategy
- status
- recent signals
- performance

## Backtesting

Allow:

- strategy selection
- symbol
- date range
- initial capital
- transaction cost
- slippage

Show:

- equity curve
- drawdown
- metrics
- trade history

## Portfolio

Show:

- holdings
- exposure
- P&L
- allocation

## AI Research

Allow users to ask research questions.

Clearly label AI-generated analysis.

---

# 29. OBSERVABILITY

Implement structured logging.

Log:

- application events
- strategy signals
- risk decisions
- orders
- execution events
- model predictions
- errors

Never log:

- API keys
- passwords
- access tokens
- secrets

Create health checks for:

- database
- Redis
- market-data provider
- broker adapter
- model service

---

# 30. ERROR HANDLING

Do not use broad silent exception handling.

Use custom exceptions.

Return useful error messages.

Implement retries only for transient failures.

Do not blindly retry order placement because that could duplicate an order.

Use idempotency keys for execution-sensitive operations.

---

# 31. SECURITY

Implement:

- environment-based secrets
- authentication-ready API design
- authorization boundaries
- request validation
- rate limiting architecture
- audit logs
- secure CORS configuration
- safe error responses

Never expose secrets to the frontend.

---

# 32. TESTING

Create comprehensive tests.

## Unit tests

Test:

- indicators
- features
- strategies
- risk rules
- position sizing
- portfolio calculations
- metrics

## Integration tests

Test:

- database
- API
- paper broker
- order lifecycle

## Backtesting tests

Use deterministic sample data.

Verify:

- trades
- P&L
- position calculations
- commissions
- slippage

## Risk tests

Verify that:

- max position is enforced
- max daily loss stops new trades
- max drawdown pauses trading
- kill switch blocks new orders

## ML tests

Verify:

- no future leakage
- correct feature columns
- deterministic preprocessing
- model input validation

Use pytest.

---

# 33. CI/CD

Create GitHub Actions.

Pipeline:

1. Install dependencies
2. Lint
3. Format check
4. Type check
5. Run unit tests
6. Run integration tests
7. Build Docker image

CI should fail on test failures.

---

# 34. DOCKER

Create:

Dockerfile
docker-compose.yml

Services:

- backend
- frontend
- postgres
- redis

The project should start locally with a simple command.

Example:

docker compose up --build

Provide health checks.

---

# 35. DEVELOPMENT EXPERIENCE

Create:

Makefile

Commands such as:

make install
make test
make lint
make format
make run
make docker-up
make docker-down
make migrate
make seed

Provide clear README instructions.

---

# 36. SAMPLE DATA

The project must work without requiring paid APIs.

Include a synthetic/sample dataset generator.

Generate realistic OHLCV-like data for development.

This allows:

- feature testing
- strategy testing
- backtesting
- API testing
- dashboard development

without external services.

Clearly label synthetic data as synthetic.

---

# 37. INITIAL STRATEGY

Build one complete baseline strategy first.

Recommended:

Moving Average Crossover.

Example:

Fast SMA = 20
Slow SMA = 50

BUY when fast SMA crosses above slow SMA.

SELL when fast SMA crosses below slow SMA.

Then pass the signal through:

Signal Engine
    ↓
Risk Manager
    ↓
Paper Broker

Do not start with an overly complex AI strategy.

---

# 38. ML STRATEGY

After the baseline strategy works, add an ML strategy.

Example target:

Predict whether the next N periods return is positive.

Features:

- RSI
- MACD
- SMA distance
- EMA distance
- ATR
- volatility
- volume change
- momentum
- recent returns

Models:

Baseline:
Logistic Regression

Then:

Random Forest

Then:

XGBoost

Compare them.

Do not select the model only by classification accuracy.

Compare:

- precision
- recall
- F1
- ROC-AUC
- strategy return
- drawdown
- Sharpe
- transaction costs
- stability across periods

---

# 39. MODEL + TRADING DECISION

Separate:

MODEL PREDICTION

from

TRADING DECISION.

Example:

Model:

Probability of positive return = 0.72

Trading rule:

Only consider BUY if probability > 0.65.

Then:

Risk Manager checks:

- position size
- current exposure
- daily loss
- drawdown
- cooldown
- trading status

Only after all checks pass should a paper order be created.

---

# 40. PERFORMANCE EVALUATION

Create a comparison report:

Strategy A:
Buy and Hold

Strategy B:
Moving Average

Strategy C:
ML Strategy

Compare:

- total return
- annualized return
- max drawdown
- Sharpe
- Sortino
- win rate
- profit factor
- number of trades
- turnover
- transaction costs

The system must clearly warn that backtest performance does not guarantee future performance.

---

# 41. ANTI-OVERFITTING

Implement safeguards:

- train/validation/test separation
- walk-forward testing
- limited hyperparameter tuning
- out-of-sample evaluation
- transaction costs
- slippage
- stability checks

Avoid repeatedly tuning against the final test set.

---

# 42. RESEARCH NOTEBOOKS

Create notebooks for:

01_data_exploration.ipynb
02_feature_engineering.ipynb
03_strategy_backtest.ipynb
04_ml_training.ipynb
05_model_evaluation.ipynb
06_walk_forward_validation.ipynb
07_portfolio_analysis.ipynb

Keep production code outside notebooks.

---

# 43. DOCUMENTATION

README must explain:

- project overview
- architecture
- setup
- configuration
- database
- data ingestion
- feature engineering
- strategies
- ML
- backtesting
- risk management
- paper trading
- AI/RAG
- API
- dashboard
- Docker
- testing
- deployment
- limitations

Create architecture diagrams using Mermaid where useful.

---

# 44. GIT COMMIT PLAN

Implement the project in logical commits.

Suggested commits:

01. Initialize project structure
02. Add configuration and logging
03. Add database and migrations
04. Add market-data abstraction
05. Add sample data generator
06. Add data validation
07. Add feature engineering
08. Add technical indicators
09. Add baseline strategy engine
10. Add backtesting engine
11. Add performance metrics
12. Add risk management
13. Add position sizing
14. Add paper broker
15. Add order management
16. Add portfolio management
17. Add ML training pipeline
18. Add ML strategy
19. Add walk-forward validation
20. Add FastAPI endpoints
21. Add React dashboard
22. Add AI/LLM service
23. Add sentiment pipeline
24. Add RAG
25. Add LangGraph research agent
26. Add monitoring
27. Add Docker
28. Add CI/CD
29. Add tests
30. Improve documentation

Do not make meaningless commits.

Each commit should leave the project in a runnable state whenever practical.

---

# 45. IMPLEMENTATION PROCESS

IMPORTANT:

Do NOT generate the entire codebase blindly in one step.

Work incrementally.

For each phase:

1. Explain the goal briefly.
2. Inspect the current project structure.
3. Create/update the required files.
4. Implement production-quality code.
5. Add tests.
6. Run tests.
7. Fix failures.
8. Explain what changed.
9. Provide exact commands to run.
10. Provide the next step.

Do not overwrite working code unnecessarily.

Before changing architecture, explain why.

---

# 46. CODE QUALITY REQUIREMENTS

Use:

- type hints
- docstrings for important public interfaces
- small functions
- dependency injection where appropriate
- clear naming
- modular architecture
- configuration-driven behavior

Avoid:

- giant files
- duplicated logic
- global mutable state
- hard-coded secrets
- hidden side effects
- unnecessary abstractions
- unused dependencies

---

# 47. FINANCIAL-SYSTEM SAFETY REQUIREMENTS

Treat every trading operation as high impact.

Default:

BROKER_MODE=paper

ENABLE_LIVE_TRADING=false

A live broker must never be activated accidentally.

Before any live execution capability is introduced, require:

1. Explicit configuration
2. Risk limits
3. Kill switch
4. Order validation
5. Audit logging
6. Paper-trading verification
7. Clear user confirmation
8. Broker connection health check

Never allow an LLM agent to directly call a live order-placement function.

The AI layer can recommend or explain.

The deterministic execution/risk layer must control order eligibility.

---

# 48. FINAL ARCHITECTURE

Target architecture:

                    ┌─────────────────────┐
                    │      React UI       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      FastAPI        │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼─────────────────┐
              │                │                 │
              ▼                ▼                 ▼
       Market Data        Strategy Engine     AI Layer
              │                │                 │
              ▼                ▼                 ▼
       Feature Engine      Signal Engine     RAG / Agents
              │                │                 │
              └────────────────┼─────────────────┘
                               ▼
                       Risk Management
                               │
                               ▼
                      Portfolio Manager
                               │
                               ▼
                       Order Management
                               │
                               ▼
                         Paper Broker
                               │
                       Optional Adapter
                               │
                               ▼
                     External Broker API

Supporting services:

PostgreSQL
Redis
Model Registry
Logging
Monitoring
Audit Logs
Background Workers

---

# 49. DEFINITION OF DONE

The project is considered complete when:

- The application starts locally.
- PostgreSQL works.
- Redis works.
- Sample market data can be generated/imported.
- Data validation works.
- Features can be generated.
- At least one rule-based strategy works.
- Backtesting works.
- Transaction costs and slippage are supported.
- Performance metrics are calculated.
- Risk management works.
- Paper trading works.
- Orders have lifecycle states.
- Portfolio P&L is calculated.
- ML training works.
- ML predictions work.
- Walk-forward validation works.
- FastAPI APIs work.
- React dashboard works.
- AI research works.
- Optional RAG works.
- Optional LangGraph workflow works.
- Tests pass.
- Docker Compose works.
- CI pipeline works.
- Documentation is complete.
- No real API keys are committed.
- Live trading is disabled by default.

---

# 50. FIRST TASK

Start by creating the repository structure and the minimum runnable application.

Do NOT implement every feature immediately.

First implement:

1. Project structure
2. Python environment configuration
3. FastAPI application
4. PostgreSQL connection
5. Redis connection
6. Configuration management
7. Structured logging
8. Health endpoint
9. Docker Compose
10. Basic pytest setup
11. README
12. .env.example

Then run the tests and health checks.

After the foundation works, proceed phase-by-phase through:

DATA
→ FEATURES
→ STRATEGIES
→ BACKTESTING
→ RISK
→ PAPER TRADING
→ ML
→ API
→ DASHBOARD
→ AI/RAG
→ AGENTS
→ MONITORING
→ DEPLOYMENT

Always prioritize correctness, testability, explainability, risk controls, and maintainability over complexity.

The final result should look like a serious AI/ML engineering portfolio project rather than a simple trading script.
