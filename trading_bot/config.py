from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SUPPORTED_PRICE_FIELDS = {"open", "high", "low", "close", "volume"}
SUPPORTED_INDICATORS = {"sma", "ema"}
SUPPORTED_OPERATORS = {">", ">=", "<", "<=", "==", "crosses_above", "crosses_below"}


class ConfigError(ValueError):
    """Raised when the trading bot configuration is invalid."""


def load_config(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ConfigError("Configuration root must be a JSON object.")
    return validate_config(data)


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    required = ["name", "symbol", "timeframe", "initial_cash", "trading_costs", "risk", "strategy"]
    for key in required:
        if key not in config:
            raise ConfigError(f"Missing required config key: {key}")

    if not isinstance(config["name"], str) or not config["name"].strip():
        raise ConfigError("name must be a non-empty string.")
    if not isinstance(config["symbol"], str) or not config["symbol"].strip():
        raise ConfigError("symbol must be a non-empty string.")
    if not isinstance(config["timeframe"], str) or not config["timeframe"].strip():
        raise ConfigError("timeframe must be a non-empty string.")
    if float(config["initial_cash"]) <= 0:
        raise ConfigError("initial_cash must be greater than zero.")

    _validate_trading_costs(config["trading_costs"])
    _validate_risk(config["risk"])
    _validate_strategy(config["strategy"])
    _apply_deployment_defaults(config)
    _validate_deployment(config["deployment"])
    if "tuning" in config:
        _validate_tuning(config["tuning"])
    return config


def _validate_trading_costs(costs: dict[str, Any]) -> None:
    if not isinstance(costs, dict):
        raise ConfigError("trading_costs must be an object.")
    fee = float(costs.get("fee_per_trade", 0.0))
    slippage = float(costs.get("slippage_bps", 0.0))
    if fee < 0:
        raise ConfigError("fee_per_trade cannot be negative.")
    if slippage < 0:
        raise ConfigError("slippage_bps cannot be negative.")
    costs.setdefault("fee_per_trade", fee)
    costs.setdefault("slippage_bps", slippage)


def _validate_risk(risk: dict[str, Any]) -> None:
    if not isinstance(risk, dict):
        raise ConfigError("risk must be an object.")
    max_position_size = float(risk.get("max_position_size", 1.0))
    if not 0 < max_position_size <= 1:
        raise ConfigError("risk.max_position_size must be between 0 and 1.")
    risk["max_position_size"] = max_position_size
    for key in ("stop_loss_pct", "take_profit_pct"):
        if key in risk and risk[key] is not None:
            value = float(risk[key])
            if value < 0:
                raise ConfigError(f"risk.{key} cannot be negative.")
            risk[key] = value


def _validate_strategy(strategy: dict[str, Any]) -> None:
    if not isinstance(strategy, dict):
        raise ConfigError("strategy must be an object.")
    indicators = strategy.get("indicators")
    if not isinstance(indicators, list) or not indicators:
        raise ConfigError("strategy.indicators must be a non-empty list.")

    seen_names: set[str] = set()
    for indicator in indicators:
        if not isinstance(indicator, dict):
            raise ConfigError("Each indicator must be an object.")
        name = indicator.get("name")
        indicator_type = indicator.get("type")
        source = indicator.get("source")
        window = indicator.get("window")
        if not isinstance(name, str) or not name:
            raise ConfigError("Each indicator requires a non-empty name.")
        if name in seen_names:
            raise ConfigError(f"Duplicate indicator name: {name}")
        seen_names.add(name)
        if indicator_type not in SUPPORTED_INDICATORS:
            raise ConfigError(f"Unsupported indicator type: {indicator_type}")
        if source not in SUPPORTED_PRICE_FIELDS:
            raise ConfigError(f"Unsupported indicator source: {source}")
        if int(window) <= 0:
            raise ConfigError(f"Indicator {name} must have a positive window.")
        indicator["window"] = int(window)

    for key in ("entry", "exit"):
        if key not in strategy:
            raise ConfigError(f"strategy must define {key} conditions.")
        _validate_condition_tree(strategy[key])


def _validate_condition_tree(node: dict[str, Any]) -> None:
    if not isinstance(node, dict):
        raise ConfigError("Conditions must be JSON objects.")

    branches = [key for key in ("all", "any") if key in node]
    if branches:
        if len(branches) > 1:
            raise ConfigError("A condition group cannot contain both 'all' and 'any'.")
        values = node[branches[0]]
        if not isinstance(values, list) or not values:
            raise ConfigError(f"Condition group '{branches[0]}' must be a non-empty list.")
        for child in values:
            _validate_condition_tree(child)
        return

    operator = node.get("operator")
    if operator not in SUPPORTED_OPERATORS:
        raise ConfigError(f"Unsupported operator: {operator}")
    _validate_operand(node.get("left"))
    _validate_operand(node.get("right"))


def _validate_operand(operand: dict[str, Any] | None) -> None:
    if not isinstance(operand, dict) or len(operand) != 1:
        raise ConfigError("Each operand must be an object with exactly one key.")
    key, value = next(iter(operand.items()))
    if key == "indicator":
        if not isinstance(value, str) or not value:
            raise ConfigError("indicator operands require a non-empty indicator name.")
        return
    if key == "price":
        if value not in SUPPORTED_PRICE_FIELDS:
            raise ConfigError(f"Unsupported price operand: {value}")
        return
    if key == "value":
        float(value)
        return
    raise ConfigError(f"Unsupported operand key: {key}")


def _apply_deployment_defaults(config: dict[str, Any]) -> None:
    deployment = config.setdefault("deployment", {})
    deployment.setdefault("target", "paper")
    deployment.setdefault("require_explicit_approval", True)
    deployment.setdefault(
        "minimum_metrics",
        {
            "total_return_pct": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown_pct": 35.0,
        },
    )


def _validate_deployment(deployment: dict[str, Any]) -> None:
    if not isinstance(deployment, dict):
        raise ConfigError("deployment must be an object.")
    if deployment.get("target") not in {"paper", "live"}:
        raise ConfigError("deployment.target must be either 'paper' or 'live'.")
    if not isinstance(deployment.get("require_explicit_approval"), bool):
        raise ConfigError("deployment.require_explicit_approval must be a boolean.")
    minimum_metrics = deployment.get("minimum_metrics")
    if not isinstance(minimum_metrics, dict):
        raise ConfigError("deployment.minimum_metrics must be an object.")
    for key, value in minimum_metrics.items():
        if key not in {"total_return_pct", "sharpe_ratio", "max_drawdown_pct", "win_rate_pct"}:
            raise ConfigError(f"Unsupported deployment metric threshold: {key}")
        float(value)


def _validate_tuning(tuning: dict[str, Any]) -> None:
    if not isinstance(tuning, dict):
        raise ConfigError("tuning must be an object.")
    parameter_space = tuning.get("parameter_space")
    if not isinstance(parameter_space, dict) or not parameter_space:
        raise ConfigError("tuning.parameter_space must be a non-empty object.")
    for path, values in parameter_space.items():
        if not isinstance(path, str) or not path:
            raise ConfigError("Each tuning parameter path must be a non-empty string.")
        if not isinstance(values, list) or not values:
            raise ConfigError(f"Tuning values for {path} must be a non-empty list.")
    rank_by = tuning.setdefault(
        "rank_by",
        [
            {"metric": "total_return_pct", "direction": "desc"},
            {"metric": "sharpe_ratio", "direction": "desc"},
            {"metric": "max_drawdown_pct", "direction": "asc"},
        ],
    )
    if not isinstance(rank_by, list) or not rank_by:
        raise ConfigError("tuning.rank_by must be a non-empty list.")
    for ranking in rank_by:
        if not isinstance(ranking, dict):
            raise ConfigError("Each rank_by entry must be an object.")
        if ranking.get("metric") not in {"total_return_pct", "sharpe_ratio", "max_drawdown_pct", "win_rate_pct"}:
            raise ConfigError(f"Unsupported ranking metric: {ranking.get('metric')}")
        if ranking.get("direction") not in {"asc", "desc"}:
            raise ConfigError("Ranking direction must be 'asc' or 'desc'.")
    if "max_runs" in tuning and int(tuning["max_runs"]) <= 0:
        raise ConfigError("tuning.max_runs must be greater than zero.")
