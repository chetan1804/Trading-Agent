from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimits:
    risk_per_trade: float = 0.01
    max_position_fraction: float = 0.10
    max_portfolio_exposure_fraction: float = 0.80
    max_open_positions: int = 10
    max_daily_loss_fraction: float = 0.02
    max_drawdown_fraction: float = 0.15
    cooldown_seconds: int = 3600

    def __post_init__(self) -> None:
        fractions = (
            self.risk_per_trade,
            self.max_position_fraction,
            self.max_portfolio_exposure_fraction,
            self.max_daily_loss_fraction,
            self.max_drawdown_fraction,
        )
        if any(not 0 < fraction <= 1 for fraction in fractions):
            raise ValueError("risk fractions must be greater than 0 and at most 1")
        if self.max_open_positions < 1:
            raise ValueError("max_open_positions must be at least 1")
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds cannot be negative")
