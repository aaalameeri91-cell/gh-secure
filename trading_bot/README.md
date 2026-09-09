# Trading Bot Foundation

This standalone module is isolated from the existing `/home/runner/work/gh-secure/gh-secure/gh-secure` CLI so the repository's security tool behavior remains unchanged.

## What it includes

- strategy input via JSON
- CSV market data ingestion
- rule-based backtesting with fees and slippage
- performance analytics and trade logs
- parameter tuning over a configurable search space
- explicit approval gate before deployment checks pass

## Supported strategy format

A strategy file defines:

- identifiers: `name`, `symbol`, `timeframe`
- capital: `initial_cash`
- trading costs: `fee_per_trade`, `slippage_bps`
- risk: `max_position_size`, optional `stop_loss_pct`, optional `take_profit_pct`
- indicators: reusable `sma` or `ema` definitions
- rules: nested `all` / `any` groups with `crosses_above`, `crosses_below`, `>`, `>=`, `<`, `<=`, `==`
- deployment gate: thresholds and `require_explicit_approval`
- tuning: parameter grid and ranking rules

## Commands

Run from `/home/runner/work/gh-secure/gh-secure`.

```bash
python3 -m trading_bot backtest \
  --config /home/runner/work/gh-secure/gh-secure/trading_bot/examples/sample_strategy.json \
  --data /home/runner/work/gh-secure/gh-secure/trading_bot/examples/sample_market_data.csv \
  --output /tmp/trading-bot/backtest.json

python3 -m trading_bot tune \
  --config /home/runner/work/gh-secure/gh-secure/trading_bot/examples/sample_strategy.json \
  --data /home/runner/work/gh-secure/gh-secure/trading_bot/examples/sample_market_data.csv \
  --output /tmp/trading-bot/tuning.json

python3 -m trading_bot deploy-check \
  --config /home/runner/work/gh-secure/gh-secure/trading_bot/examples/sample_strategy.json \
  --backtest /tmp/trading-bot/backtest.json \
  --approval-store /tmp/trading-bot/approvals.json

python3 -m trading_bot approve \
  --config /home/runner/work/gh-secure/gh-secure/trading_bot/examples/sample_strategy.json \
  --backtest /tmp/trading-bot/backtest.json \
  --approval-store /tmp/trading-bot/approvals.json \
  --output /tmp/trading-bot/approval.json
```

## Safety controls

- validates required strategy fields and supported rule syntax
- rejects unordered or malformed market data
- executes signals on the next candle to reduce look-ahead bias
- keeps deployment checks separate from backtesting and approval
- blocks deployment until thresholds pass and approval is recorded
