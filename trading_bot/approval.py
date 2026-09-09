from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def make_recommendation(summary: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    deployment = config["deployment"]
    minimum_metrics = deployment["minimum_metrics"]
    reasons: list[str] = []
    eligible = True
    for metric, threshold in minimum_metrics.items():
        value = summary.get(metric)
        threshold_value = float(threshold)
        if value is None:
            eligible = False
            reasons.append(f"{metric} is unavailable.")
            continue
        if metric == "max_drawdown_pct":
            if value > threshold_value:
                eligible = False
                reasons.append(f"{metric}={value} exceeds threshold {threshold_value}.")
        elif value < threshold_value:
            eligible = False
            reasons.append(f"{metric}={value} is below threshold {threshold_value}.")
    if eligible:
        reasons.append("All configured deployment thresholds passed.")
    return {
        "target": deployment["target"],
        "explicit_approval_required": deployment["require_explicit_approval"],
        "eligible_for_deployment": eligible,
        "reasons": reasons,
    }


def approve_strategy(config: dict[str, Any], backtest_result: dict[str, Any], approval_store: str | Path) -> dict[str, Any]:
    store_path = Path(approval_store)
    payload = _load_store(store_path)
    fingerprint = config_fingerprint(config)
    approval = {
        "config_name": config["name"],
        "config_fingerprint": fingerprint,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "approved_target": config["deployment"]["target"],
        "summary": backtest_result["summary"],
        "recommendation": backtest_result["recommendation"],
    }
    approvals = [item for item in payload["approvals"] if item["config_fingerprint"] != fingerprint]
    approvals.append(approval)
    payload["approvals"] = approvals
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return approval


def deployment_status(config: dict[str, Any], backtest_result: dict[str, Any], approval_store: str | Path) -> dict[str, Any]:
    store = _load_store(Path(approval_store))
    fingerprint = config_fingerprint(config)
    approved = any(item["config_fingerprint"] == fingerprint for item in store["approvals"])
    recommendation = backtest_result["recommendation"]
    blocked_reasons = [] if recommendation["eligible_for_deployment"] else list(recommendation["reasons"])
    if recommendation["explicit_approval_required"] and not approved:
        blocked_reasons.append("Strategy is blocked until you explicitly approve it.")
    return {
        "config_name": config["name"],
        "target": config["deployment"]["target"],
        "approved": approved,
        "eligible_for_deployment": recommendation["eligible_for_deployment"],
        "can_deploy": recommendation["eligible_for_deployment"] and (approved or not recommendation["explicit_approval_required"]),
        "blocked_reasons": blocked_reasons,
    }


def config_fingerprint(config: dict[str, Any]) -> str:
    serialized = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _load_store(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"approvals": []}
    return json.loads(path.read_text(encoding="utf-8"))
