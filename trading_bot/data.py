from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Candle:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


def load_market_data(path: str | Path) -> list[Candle]:
    rows: list[Candle] = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"timestamp", "open", "high", "low", "close"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("CSV market data must include timestamp, open, high, low, and close columns.")
        previous_timestamp = None
        for raw_row in reader:
            candle = Candle(
                timestamp=raw_row["timestamp"],
                open=float(raw_row["open"]),
                high=float(raw_row["high"]),
                low=float(raw_row["low"]),
                close=float(raw_row["close"]),
                volume=float(raw_row.get("volume") or 0.0),
            )
            if previous_timestamp is not None and candle.timestamp <= previous_timestamp:
                raise ValueError("Market data must be ordered by strictly increasing timestamp.")
            if candle.low > min(candle.open, candle.high, candle.close):
                raise ValueError(f"Invalid candle at {candle.timestamp}: low exceeds price range.")
            if candle.high < max(candle.open, candle.low, candle.close):
                raise ValueError(f"Invalid candle at {candle.timestamp}: high is below price range.")
            previous_timestamp = candle.timestamp
            rows.append(candle)
    if len(rows) < 2:
        raise ValueError("At least two rows of market data are required for backtesting.")
    return rows
