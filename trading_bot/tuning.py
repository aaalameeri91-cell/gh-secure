from __future__ import annotations

import copy
import itertools
from typing import Any

from .config import validate_config
from .engine import run_backtest


def run_tuning(config: dict[str, Any], candles: list[Any]) -> dict[str, Any]:
    tuning = config.get("tuning")
    if not tuning:
        raise ValueError("This configuration does not define a tuning section.")

    parameter_space = tuning["parameter_space"]
    parameter_names = list(parameter_space)
    parameter_values = [parameter_space[name] for name in parameter_names]
    rank_by = tuning["rank_by"]
    max_runs = int(tuning.get("max_runs", 0)) or None

    runs: list[dict[str, Any]] = []
    for combo_index, combo in enumerate(itertools.product(*parameter_values), start=1):
        if max_runs is not None and combo_index > max_runs:
            break
        candidate_config = copy.deepcopy(config)
        overrides = dict(zip(parameter_names, combo, strict=True))
        for path, value in overrides.items():
            _set_nested_value(candidate_config, path, value)
        validate_config(candidate_config)
        result = run_backtest(candidate_config, candles)
        runs.append(
            {
                "parameters": overrides,
                "summary": result["summary"],
                "recommendation": result["recommendation"],
            }
        )

    runs.sort(key=lambda item: _ranking_key(item["summary"], rank_by))
    for rank, run in enumerate(runs, start=1):
        run["rank"] = rank
    return {
        "config_name": config["name"],
        "tested_runs": len(runs),
        "best_run": runs[0] if runs else None,
        "runs": runs,
    }


def _set_nested_value(payload: dict[str, Any], path: str, value: Any) -> None:
    current: Any = payload
    parts = path.split(".")
    for part in parts[:-1]:
        current = current[int(part)] if part.isdigit() else current[part]
    final_key = parts[-1]
    if final_key.isdigit():
        current[int(final_key)] = value
    else:
        current[final_key] = value


def _ranking_key(summary: dict[str, Any], rank_by: list[dict[str, str]]) -> tuple[float, ...]:
    key: list[float] = []
    for ranking in rank_by:
        metric = ranking["metric"]
        direction = ranking["direction"]
        value = summary.get(metric)
        safe_value = float("inf") if value is None and direction == "asc" else float("-inf") if value is None else float(value)
        key.append(safe_value if direction == "asc" else -safe_value)
    return tuple(key)
