from __future__ import annotations

from typing import Iterable

from .data import Candle


def build_indicator_map(indicators: list[dict], candles: list[Candle]) -> dict[str, list[float | None]]:
    result: dict[str, list[float | None]] = {}
    for indicator in indicators:
        series = [getattr(candle, indicator["source"]) for candle in candles]
        indicator_type = indicator["type"]
        if indicator_type == "sma":
            values = simple_moving_average(series, indicator["window"])
        elif indicator_type == "ema":
            values = exponential_moving_average(series, indicator["window"])
        else:
            raise ValueError(f"Unsupported indicator type: {indicator_type}")
        result[indicator["name"]] = values
    return result


def simple_moving_average(series: Iterable[float], window: int) -> list[float | None]:
    values = list(series)
    output: list[float | None] = [None] * len(values)
    running_total = 0.0
    for index, value in enumerate(values):
        running_total += value
        if index >= window:
            running_total -= values[index - window]
        if index >= window - 1:
            output[index] = running_total / window
    return output


def exponential_moving_average(series: Iterable[float], window: int) -> list[float | None]:
    values = list(series)
    output: list[float | None] = [None] * len(values)
    smoothing = 2 / (window + 1)
    ema = None
    for index, value in enumerate(values):
        if ema is None:
            ema = value
        else:
            ema = (value * smoothing) + (ema * (1 - smoothing))
        if index >= window - 1:
            output[index] = ema
    return output
