from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .approval import approve_strategy, deployment_status
from .config import load_config
from .data import load_market_data
from .engine import run_backtest
from .tuning import run_tuning


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "backtest":
        result = run_backtest(load_config(args.config), load_market_data(args.data))
        _emit(args.output, result)
        return 0
    if args.command == "tune":
        result = run_tuning(load_config(args.config), load_market_data(args.data))
        _emit(args.output, result)
        return 0
    if args.command == "approve":
        config = load_config(args.config)
        backtest_result = _load_json(args.backtest)
        result = approve_strategy(config, backtest_result, args.approval_store)
        _emit(args.output, result)
        return 0
    if args.command == "deploy-check":
        config = load_config(args.config)
        backtest_result = _load_json(args.backtest)
        result = deployment_status(config, backtest_result, args.approval_store)
        _emit(args.output, result)
        return 0 if result["can_deploy"] else 2

    parser.error("Unknown command.")
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone trading bot foundation with backtesting and approval gates.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backtest = subparsers.add_parser("backtest", help="Run a backtest using a strategy config and CSV market data.")
    backtest.add_argument("--config", required=True, help="Path to the strategy JSON configuration.")
    backtest.add_argument("--data", required=True, help="Path to the CSV market data file.")
    backtest.add_argument("--output", help="Optional JSON output path.")

    tune = subparsers.add_parser("tune", help="Run parameter tuning defined inside the strategy config.")
    tune.add_argument("--config", required=True, help="Path to the strategy JSON configuration.")
    tune.add_argument("--data", required=True, help="Path to the CSV market data file.")
    tune.add_argument("--output", help="Optional JSON output path.")

    approve = subparsers.add_parser("approve", help="Approve a tested strategy for deployment checks.")
    approve.add_argument("--config", required=True, help="Path to the strategy JSON configuration.")
    approve.add_argument("--backtest", required=True, help="Path to a saved backtest JSON result.")
    approve.add_argument("--approval-store", required=True, help="Path to the JSON approval store.")
    approve.add_argument("--output", help="Optional JSON output path.")

    deploy = subparsers.add_parser("deploy-check", help="Check if a strategy is eligible and approved for deployment.")
    deploy.add_argument("--config", required=True, help="Path to the strategy JSON configuration.")
    deploy.add_argument("--backtest", required=True, help="Path to a saved backtest JSON result.")
    deploy.add_argument("--approval-store", required=True, help="Path to the JSON approval store.")
    deploy.add_argument("--output", help="Optional JSON output path.")

    return parser


def _emit(output_path: str | None, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, indent=2)
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def _load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
