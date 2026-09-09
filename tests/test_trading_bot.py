from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from trading_bot import approve_strategy, deployment_status, load_config, load_market_data, run_backtest, run_tuning


REPO_ROOT = Path("/home/runner/work/gh-secure/gh-secure")
CONFIG_PATH = REPO_ROOT / "trading_bot/examples/sample_strategy.json"
DATA_PATH = REPO_ROOT / "trading_bot/examples/sample_market_data.csv"


class TradingBotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(CONFIG_PATH)
        self.candles = load_market_data(DATA_PATH)

    def test_backtest_generates_summary_and_trade_log(self) -> None:
        result = run_backtest(self.config, self.candles)
        self.assertGreaterEqual(result["summary"]["total_trades"], 1)
        self.assertIn("eligible_for_deployment", result["recommendation"])
        self.assertEqual(len(result["equity_curve"]), len(self.candles))

    def test_tuning_returns_ranked_runs(self) -> None:
        result = run_tuning(self.config, self.candles)
        self.assertEqual(result["runs"][0]["rank"], 1)
        self.assertEqual(result["tested_runs"], len(result["runs"]))

    def test_deployment_requires_approval_then_allows_after_approval(self) -> None:
        result = run_backtest(self.config, self.candles)
        with tempfile.TemporaryDirectory() as temp_dir:
            store = Path(temp_dir) / "approvals.json"
            status_before = deployment_status(self.config, result, store)
            self.assertFalse(status_before["can_deploy"])
            approval = approve_strategy(self.config, result, store)
            self.assertEqual(approval["config_name"], self.config["name"])
            status_after = deployment_status(self.config, result, store)
            self.assertTrue(status_after["approved"])
            if result["recommendation"]["eligible_for_deployment"]:
                self.assertTrue(status_after["can_deploy"])

    def test_backtest_result_is_json_serializable(self) -> None:
        result = run_backtest(self.config, self.candles)
        json.dumps(result)


if __name__ == "__main__":
    unittest.main()
