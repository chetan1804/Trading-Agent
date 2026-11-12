# Research notebooks

These notebooks provide reproducible examples using the platform's production modules. They use synthetic data by default, which is labeled and must not be treated as actual market performance.

From the repository root, install the project and launch Jupyter with:

```sh
uv sync --extra dev
uv run --with jupyter jupyter lab notebooks
```

Run the notebooks in order when exploring the full workflow:

1. `01_data_exploration.ipynb` — inspect sample OHLCV and validation reports.
2. `02_feature_engineering.ipynb` — calculate causal indicators and check future-data isolation.
3. `03_strategy_backtest.ipynb` — compare moving-average crossover with Buy & Hold.
4. `04_ml_training.ipynb` — fit a Logistic Regression on chronological, purged training rows.
5. `05_model_evaluation.ipynb` — compare classifiers on one chronological holdout.
6. `06_walk_forward_validation.ipynb` — inspect repeated held-out test folds.
7. `07_portfolio_analysis.ipynb` — review paper account cash, exposure, and P&L accounting.

The notebooks are for exploration. Production logic remains in `backend/trading`; any change to it should be covered by the normal automated test suite.
