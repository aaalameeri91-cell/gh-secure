from __future__ import annotations

from typing import Any

from .data import Candle


def evaluate_condition(node: dict[str, Any], index: int, candles: list[Candle], indicators: dict[str, list[float | None]]) -> bool:
    if "all" in node:
        return all(evaluate_condition(child, index, candles, indicators) for child in node["all"])
    if "any" in node:
        return any(evaluate_condition(child, index, candles, indicators) for child in node["any"])

    operator = node["operator"]
    left_current, left_previous = _resolve_operand(node["left"], index, candles, indicators)
    right_current, right_previous = _resolve_operand(node["right"], index, candles, indicators)

    if operator == "crosses_above":
        return _crosses(left_current, left_previous, right_current, right_previous, direction="above")
    if operator == "crosses_below":
        return _crosses(left_current, left_previous, right_current, right_previous, direction="below")
    if left_current is None or right_current is None:
        return False
    if operator == ">":
        return left_current > right_current
    if operator == ">=":
        return left_current >= right_current
    if operator == "<":
        return left_current < right_current
    if operator == "<=":
        return left_current <= right_current
    if operator == "==":
        return left_current == right_current
    raise ValueError(f"Unsupported operator: {operator}")


def _resolve_operand(
    operand: dict[str, Any],
    index: int,
    candles: list[Candle],
    indicators: dict[str, list[float | None]],
) -> tuple[float | None, float | None]:
    key, value = next(iter(operand.items()))
    if key == "indicator":
        values = indicators[value]
        current = values[index]
        previous = values[index - 1] if index > 0 else None
        return current, previous
    if key == "price":
        current = getattr(candles[index], value)
        previous = getattr(candles[index - 1], value) if index > 0 else None
        return current, previous
    if key == "value":
        numeric = float(value)
        return numeric, numeric
    raise ValueError(f"Unsupported operand type: {key}")


def _crosses(
    left_current: float | None,
    left_previous: float | None,
    right_current: float | None,
    right_previous: float | None,
    direction: str,
) -> bool:
    if None in {left_current, left_previous, right_current, right_previous}:
        return False
    if direction == "above":
        return left_previous <= right_previous and left_current > right_current
    return left_previous >= right_previous and left_current < right_current
