from datetime import UTC, datetime, timedelta

import pytest
from app.config import Settings
from trading.risk.limits import RiskLimits
from trading.risk.manager import AccountRiskState, RiskManager, TradeProposal
from trading.risk.position_sizing import size_position

NOW = datetime(2024, 1, 2, tzinfo=UTC)


def _proposal(
    side: str = "BUY",
    *,
    stop_loss_price: float | None = 95,
    reduce_quantity: float | None = None,
) -> TradeProposal:
    return TradeProposal(
        symbol="DEMO",
        side=side,  # type: ignore[arg-type]
        entry_price=100,
        timestamp=NOW,
        stop_loss_price=stop_loss_price,
        reduce_quantity=reduce_quantity,
    )


def _account(**overrides: object) -> AccountRiskState:
    values: dict[str, object] = {
        "equity": 100_000.0,
        "available_cash": 100_000.0,
    }
    values.update(overrides)
    return AccountRiskState(**values)  # type: ignore[arg-type]


def test_position_size_uses_stop_risk_and_exposure_caps() -> None:
    size = size_position(
        equity=100_000,
        available_cash=100_000,
        entry_price=100,
        stop_loss_price=95,
        risk_fraction=0.01,
        max_position_notional=30_000,
    )

    assert size.quantity == pytest.approx(200)
    assert size.capital_required == pytest.approx(20_000)
    assert size.estimated_risk == pytest.approx(1_000)


def test_sizing_caps_position_by_cash_and_notional() -> None:
    size = size_position(
        equity=100_000,
        available_cash=2_000,
        entry_price=100,
        stop_loss_price=99,
        risk_fraction=0.01,
        max_position_notional=1_000,
    )

    assert size.quantity == pytest.approx(10)
    assert size.capital_required == pytest.approx(1_000)
    assert size.estimated_risk == pytest.approx(10)


def test_manager_fails_closed_and_requires_a_stop() -> None:
    disabled = RiskManager()
    enabled = RiskManager(enabled=True)

    assert disabled.evaluate(_proposal(), _account()).reason == "trading kill switch is disabled"
    decision = enabled.evaluate(_proposal(stop_loss_price=None), _account())
    assert not decision.approved
    assert "stop-loss" in decision.reason


@pytest.mark.parametrize(
    ("account_changes", "limits", "expected_reason"),
    [
        ({"daily_pnl": -2_000}, RiskLimits(), "maximum daily loss"),
        ({"equity": 80_000, "peak_equity": 100_000}, RiskLimits(), "maximum drawdown"),
        ({"positions": {"OTHER": 1}}, RiskLimits(max_open_positions=1), "maximum open positions"),
        ({"current_exposure": 80_000}, RiskLimits(), "maximum portfolio exposure"),
        (
            {"last_trade_at_by_symbol": {"DEMO": NOW - timedelta(minutes=30)}},
            RiskLimits(),
            "cooldown",
        ),
    ],
)
def test_manager_blocks_limit_violations(
    account_changes: dict[str, object],
    limits: RiskLimits,
    expected_reason: str,
) -> None:
    decision = RiskManager(limits, enabled=True).evaluate(_proposal(), _account(**account_changes))

    assert not decision.approved
    assert expected_reason in decision.reason


def test_manager_approves_sized_position_within_limits() -> None:
    decision = RiskManager(enabled=True).evaluate(_proposal(), _account())

    assert decision.approved
    assert decision.quantity == pytest.approx(100)
    assert decision.capital_required == pytest.approx(10_000)
    assert decision.estimated_risk == pytest.approx(500)


def test_cooldown_is_per_symbol() -> None:
    account = _account(
        last_trade_at_by_symbol={"OTHER": NOW - timedelta(minutes=1)},
    )

    decision = RiskManager(enabled=True).evaluate(_proposal(), account)

    assert decision.approved


def test_sell_reduction_is_allowed_while_kill_switch_is_off() -> None:
    decision = RiskManager(enabled=False).evaluate(
        _proposal(side="SELL", stop_loss_price=None),
        _account(positions={"DEMO": 10}),
    )

    assert decision.approved
    assert decision.quantity == 10


def test_sell_cannot_increase_a_position() -> None:
    decision = RiskManager(enabled=False).evaluate(
        _proposal(side="SELL", stop_loss_price=None, reduce_quantity=11),
        _account(positions={"DEMO": 10}),
    )

    assert not decision.approved
    assert "no greater than the open position" in decision.reason


def test_settings_default_to_trading_disabled() -> None:
    assert Settings().enable_trading is False


def test_risk_limits_validate_fraction_ranges() -> None:
    with pytest.raises(ValueError, match="risk fractions"):
        RiskLimits(risk_per_trade=0)


def test_non_finite_account_values_are_rejected() -> None:
    decision = RiskManager(enabled=True).evaluate(_proposal(), _account(equity=float("nan")))

    assert not decision.approved
    assert "must be finite" in decision.reason
