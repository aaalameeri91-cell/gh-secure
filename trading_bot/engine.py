from __future__ import annotations

from typing import Any

from .analytics import summarize
from .approval import make_recommendation
from .data import Candle
from .indicators import build_indicator_map
from .rules import evaluate_condition


def run_backtest(config: dict[str, Any], candles: list[Candle]) -> dict[str, Any]:
    indicators = build_indicator_map(config["strategy"]["indicators"], candles)
    costs = config["trading_costs"]
    risk = config["risk"]

    cash = float(config["initial_cash"])
    initial_cash = cash
    equity_curve: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    position: dict[str, Any] | None = None
    pending_action: str | None = None
    pending_reason: str | None = None

    for index, candle in enumerate(candles):
        if pending_action == "enter" and position is None:
            position = _open_position(candle, cash, risk, costs)
            if position is not None:
                cash -= position["cash_outflow"]
            pending_action = None
            pending_reason = None
        elif pending_action == "exit" and position is not None:
            cash, trade = _close_position(position, candle.timestamp, candle.open, cash, costs, pending_reason or "scheduled_exit")
            trades.append(trade)
            position = None
            pending_action = None
            pending_reason = None

        if position is not None:
            stop_triggered = position["stop_price"] is not None and candle.low <= position["stop_price"]
            take_triggered = position["take_profit_price"] is not None and candle.high >= position["take_profit_price"]
            intrabar_reason = None
            intrabar_price = None
            if stop_triggered:
                intrabar_reason = "stop_loss"
                intrabar_price = position["stop_price"]
            elif take_triggered:
                intrabar_reason = "take_profit"
                intrabar_price = position["take_profit_price"]
            if intrabar_price is not None:
                cash, trade = _close_position(position, candle.timestamp, intrabar_price, cash, costs, intrabar_reason)
                trades.append(trade)
                position = None
                pending_action = None
                pending_reason = None

        if index < len(candles) - 1:
            if position is None and evaluate_condition(config["strategy"]["entry"], index, candles, indicators):
                pending_action = "enter"
                pending_reason = "entry_rule"
            elif position is not None and evaluate_condition(config["strategy"]["exit"], index, candles, indicators):
                pending_action = "exit"
                pending_reason = "exit_rule"

        market_value = (position["quantity"] * candle.close) if position is not None else 0.0
        equity_curve.append(
            {
                "timestamp": candle.timestamp,
                "cash": round(cash, 2),
                "position_value": round(market_value, 2),
                "equity": round(cash + market_value, 2),
                "in_position": position is not None,
            }
        )

    if position is not None:
        last_candle = candles[-1]
        cash, trade = _close_position(position, last_candle.timestamp, last_candle.close, cash, costs, "end_of_backtest")
        trades.append(trade)
        equity_curve[-1] = {
            "timestamp": last_candle.timestamp,
            "cash": round(cash, 2),
            "position_value": 0.0,
            "equity": round(cash, 2),
            "in_position": False,
        }

    summary = summarize(initial_cash, equity_curve, trades, config["timeframe"])
    recommendation = make_recommendation(summary, config)
    return {
        "config_name": config["name"],
        "symbol": config["symbol"],
        "timeframe": config["timeframe"],
        "summary": summary,
        "recommendation": recommendation,
        "equity_curve": equity_curve,
        "trades": trades,
    }


def _open_position(candle: Candle, cash: float, risk: dict[str, Any], costs: dict[str, Any]) -> dict[str, Any] | None:
    fee = float(costs["fee_per_trade"])
    max_position_cash = cash * float(risk["max_position_size"])
    fill_price = _apply_slippage(candle.open, "buy", costs)
    available_cash = max_position_cash - fee
    if available_cash <= 0 or fill_price <= 0:
        return None
    quantity = available_cash / fill_price
    if quantity <= 0:
        return None
    cash_outflow = (quantity * fill_price) + fee
    stop_loss_pct = risk.get("stop_loss_pct")
    take_profit_pct = risk.get("take_profit_pct")
    return {
        "entry_time": candle.timestamp,
        "entry_price": fill_price,
        "quantity": quantity,
        "entry_fee": fee,
        "cash_outflow": cash_outflow,
        "stop_price": fill_price * (1 - stop_loss_pct) if stop_loss_pct is not None else None,
        "take_profit_price": fill_price * (1 + take_profit_pct) if take_profit_pct is not None else None,
    }


def _close_position(
    position: dict[str, Any],
    exit_time: str,
    reference_price: float,
    cash: float,
    costs: dict[str, Any],
    reason: str,
) -> tuple[float, dict[str, Any]]:
    fee = float(costs["fee_per_trade"])
    exit_price = _apply_slippage(reference_price, "sell", costs)
    proceeds = (position["quantity"] * exit_price) - fee
    updated_cash = cash + proceeds
    entry_cost = (position["quantity"] * position["entry_price"]) + position["entry_fee"]
    pnl = proceeds - entry_cost
    trade = {
        "entry_time": position["entry_time"],
        "exit_time": exit_time,
        "entry_price": round(position["entry_price"], 4),
        "exit_price": round(exit_price, 4),
        "quantity": round(position["quantity"], 8),
        "entry_fee": round(position["entry_fee"], 2),
        "exit_fee": round(fee, 2),
        "pnl": round(pnl, 2),
        "pnl_pct": round((pnl / entry_cost) * 100, 4) if entry_cost else 0.0,
        "reason": reason,
    }
    return updated_cash, trade


def _apply_slippage(price: float, side: str, costs: dict[str, Any]) -> float:
    slippage_bps = float(costs["slippage_bps"])
    multiplier = 1 + (slippage_bps / 10000) if side == "buy" else 1 - (slippage_bps / 10000)
    return price * multiplier
