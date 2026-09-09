from __future__ import annotations

import math
from statistics import mean, pstdev
from typing import Any


def summarize(initial_cash: float, equity_curve: list[dict[str, Any]], trades: list[dict[str, Any]], timeframe: str) -> dict[str, Any]:
    equity_values = [point["equity"] for point in equity_curve]
    final_equity = equity_values[-1]
    total_return_pct = ((final_equity - initial_cash) / initial_cash) * 100
    max_drawdown_pct = _max_drawdown(equity_values)
    returns = _returns(equity_values)
    sharpe_ratio = _sharpe_ratio(returns, timeframe)
    wins = [trade for trade in trades if trade["pnl"] > 0]
    losses = [trade for trade in trades if trade["pnl"] < 0]
    gross_profit = sum(trade["pnl"] for trade in wins)
    gross_loss = sum(trade["pnl"] for trade in losses)
    win_rate_pct = (len(wins) / len(trades) * 100) if trades else 0.0
    profit_factor = (gross_profit / abs(gross_loss)) if gross_loss else None
    average_trade_pnl = mean([trade["pnl"] for trade in trades]) if trades else 0.0
    return {
        "initial_cash": round(initial_cash, 2),
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return_pct, 4),
        "max_drawdown_pct": round(max_drawdown_pct, 4),
        "sharpe_ratio": round(sharpe_ratio, 4),
        "total_trades": len(trades),
        "win_rate_pct": round(win_rate_pct, 4),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "profit_factor": round(profit_factor, 4) if profit_factor is not None else None,
        "average_trade_pnl": round(average_trade_pnl, 2),
    }


def _returns(equity_values: list[float]) -> list[float]:
    output: list[float] = []
    for previous, current in zip(equity_values, equity_values[1:]):
        if previous == 0:
            output.append(0.0)
        else:
            output.append((current - previous) / previous)
    return output


def _max_drawdown(equity_values: list[float]) -> float:
    peak = equity_values[0]
    drawdown = 0.0
    for equity in equity_values:
        peak = max(peak, equity)
        if peak == 0:
            continue
        drawdown = max(drawdown, ((peak - equity) / peak) * 100)
    return drawdown


def _sharpe_ratio(returns: list[float], timeframe: str) -> float:
    if len(returns) < 2:
        return 0.0
    deviation = pstdev(returns)
    if deviation == 0:
        return 0.0
    annualization = _annualization_factor(timeframe)
    return (mean(returns) / deviation) * math.sqrt(annualization)


def _annualization_factor(timeframe: str) -> int:
    normalized = timeframe.upper()
    if normalized.endswith("D"):
        return 252
    if normalized.endswith("H"):
        hours = int(normalized[:-1] or 1)
        return max(1, (24 // max(hours, 1)) * 252)
    return 252
