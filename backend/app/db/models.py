from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Float, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MarketBar(Base):
    __tablename__ = "market_data"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)


class PaperOrderRecord(Base):
    __tablename__ = "paper_orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    order_type: Mapped[str] = mapped_column(String(8), nullable=False)
    limit_price: Mapped[float | None] = mapped_column(Float)
    stop_price: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    filled_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_fill_price: Mapped[float | None] = mapped_column(Float)
    rejection_reason: Mapped[str | None] = mapped_column(String(500))


class PaperPortfolioRecord(Base):
    __tablename__ = "paper_portfolios"

    account_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    initial_cash: Mapped[float] = mapped_column(Float, nullable=False)
    cash: Mapped[float] = mapped_column(Float, nullable=False)
    positions: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    last_prices: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    position_cost_basis: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Float, nullable=False)
    daily_pnl: Mapped[float] = mapped_column(Float, nullable=False)
    peak_equity: Mapped[float] = mapped_column(Float, nullable=False)
    last_trade_at_by_symbol: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)


class RegisteredModel(Base):
    __tablename__ = "registered_models"

    model_version: Mapped[str] = mapped_column(String(64), primary_key=True)
    model_type: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(80), nullable=False)
    training_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    feature_names: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    hyperparameters: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    metrics: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    validation_metrics: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    split_rows: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    artifact: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
