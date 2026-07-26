"""
analytics.py
------------
Quantitative helpers that turn raw project inputs into portfolio-grade
project-management insight:

- A **risk scoring model** (probability × impact → score → risk level).
- A **project health indicator** (Green / Yellow / Red) with reasons.
- Small **aggregation helpers** used by the dashboard (open action items,
  high-risk counts, and health distribution across saved projects).

Everything here is pure-Python, deterministic, and dependency-free so it can be
unit-tested and reused by both the engine (src/ai_engine.py) and the UI
(app.py) without side effects.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .utils import clean_lines, parse_date, safe_get

# ---------------------------------------------------------------------------
# Risk scoring model
# ---------------------------------------------------------------------------
# Probability and impact are scored on a 1–5 scale using light keyword
# heuristics. Risk score = probability × impact (1–25), mapped to a level.

_PROB_KEYWORDS = {
    5: ("will ", "certain", "already", "ongoing"),
    4: ("adopt", "user", "training", "change", "timeline", "delay", "schedule", "scope creep"),
    2: ("unlikely", "rare", "minor"),
}
_IMPACT_KEYWORDS = {
    5: ("security", "compliance", "safety", "legal", "outage", "breach", "critical"),
    4: ("data", "migration", "accuracy", "quality", "budget", "cost", "resource", "availab", "capacity"),
    2: ("cosmetic", "minor", "low"),
}

_LEVEL_LABELS = {
    "Low": "🟢 Low",
    "Medium": "🟡 Medium",
    "High": "🟠 High",
    "Critical": "🔴 Critical",
}


def _keyword_score(text: str, table: dict[int, tuple[str, ...]], default: int = 3) -> int:
    """Return the score for the first matching keyword bucket, else default."""
    lowered = text.lower()
    # Check higher-severity buckets first so they win ties.
    for value in sorted(table, reverse=True):
        if any(kw in lowered for kw in table[value]):
            return value
    return default


def risk_level(score: int) -> str:
    """Map a 1–25 risk score to a qualitative level."""
    if score >= 15:
        return "Critical"
    if score >= 9:
        return "High"
    if score >= 4:
        return "Medium"
    return "Low"


def _mitigation_for(text: str) -> str:
    """Suggest a tailored mitigation based on the risk wording."""
    t = text.lower()
    if any(k in t for k in ("adopt", "user", "training", "change")):
        return "Engage users early; provide training and quick-reference guides."
    if any(k in t for k in ("data", "migration", "quality", "accuracy")):
        return "Validate and clean data; run a pilot before full cutover."
    if any(k in t for k in ("budget", "cost", "resource", "availab", "capacity")):
        return "Confirm resource commitments; escalate gaps to the sponsor."
    if any(k in t for k in ("time", "timeline", "delay", "schedule")):
        return "Prioritize scope; track progress weekly and flag slippage early."
    if any(k in t for k in ("security", "compliance", "safety", "legal")):
        return "Involve compliance/security early; add review gates before go-live."
    return "Assign an owner, monitor regularly, and define a mitigation plan."


def assess_risk(text: str) -> dict[str, Any]:
    """
    Score a single risk.

    Returns a dict with numeric probability/impact (1–5), the computed score,
    the qualitative level, matching labels, and a suggested mitigation.
    """
    probability = _keyword_score(text, _PROB_KEYWORDS)
    impact = _keyword_score(text, _IMPACT_KEYWORDS)
    score = probability * impact
    level = risk_level(score)
    return {
        "risk": text,
        "probability": probability,
        "impact": impact,
        "score": score,
        "level": level,
        "level_label": _LEVEL_LABELS[level],
        "mitigation": _mitigation_for(text),
    }


def score_risks(risks: list[str]) -> list[dict[str, Any]]:
    """Score a list of risks, sorted highest-score first."""
    scored = [assess_risk(r) for r in risks if r]
    return sorted(scored, key=lambda r: r["score"], reverse=True)


def risks_from_inputs(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract and score the risks listed in a project's inputs."""
    risks = clean_lines(safe_get(inputs, "known_risks"))
    if not risks:
        risks = ["Timeline pressure may impact quality."]
    return score_risks(risks)


# ---------------------------------------------------------------------------
# Project health indicator (Green / Yellow / Red)
# ---------------------------------------------------------------------------
_HEALTH_ORDER = {"Green": 0, "Yellow": 1, "Red": 2}
_HEALTH_EMOJI = {"Green": "🟢", "Yellow": "🟡", "Red": "🔴"}


def _worse(a: str, b: str) -> str:
    """Return the more severe of two health statuses."""
    return a if _HEALTH_ORDER[a] >= _HEALTH_ORDER[b] else b


def compute_health(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Derive a Red/Yellow/Green health status from a project's inputs.

    Heuristics (deliberately simple and explainable):
    - 3+ high/critical risks  -> Red
    - 1–2 high/critical risks  -> at least Yellow
    - Target date in the past  -> at least Yellow
    - Missing required context  -> at least Yellow
    """
    scored = risks_from_inputs(inputs)
    high = [r for r in scored if r["level"] in ("High", "Critical")]

    status = "Green"
    reasons: list[str] = []

    if len(high) >= 3:
        status = _worse(status, "Red")
        reasons.append(f"{len(high)} high/critical risks identified.")
    elif len(high) >= 1:
        status = _worse(status, "Yellow")
        reasons.append(f"{len(high)} elevated risk(s) to monitor.")

    target = parse_date(safe_get(inputs, "target_date"))
    if target and target < date.today():
        status = _worse(status, "Yellow")
        reasons.append("Target completion date is in the past.")

    for key, label in (("objective", "objective"), ("business_problem", "business problem")):
        if not safe_get(inputs, key):
            status = _worse(status, "Yellow")
            reasons.append(f"Missing {label}.")

    if not reasons:
        reasons.append("No elevated risks; key information is complete.")

    return {
        "status": status,
        "emoji": _HEALTH_EMOJI[status],
        "label": f"{_HEALTH_EMOJI[status]} {status}",
        "reasons": reasons,
        "high_risk_count": len(high),
        "risk_count": len(scored),
    }


# ---------------------------------------------------------------------------
# Dashboard aggregation helpers
# ---------------------------------------------------------------------------
def count_open_action_items(outputs: dict[str, str] | None) -> int:
    """Count 'Open' rows in the generated Action Item List (Markdown table)."""
    if not outputs:
        return 0
    return outputs.get("actions", "").count("| Open |")


def summarize_project(record: dict[str, Any]) -> dict[str, Any]:
    """
    Build a compact analytics summary for one saved project record.

    `record` is the dict returned by db.get_project (has inputs + outputs).
    """
    inputs = record.get("inputs", {})
    outputs = record.get("outputs", {})
    health = compute_health(inputs)
    return {
        "id": record.get("id"),
        "name": record.get("name", "Untitled"),
        "health": health["status"],
        "health_label": health["label"],
        "high_risks": health["high_risk_count"],
        "open_actions": count_open_action_items(outputs),
    }


def dashboard_metrics(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-project summaries into portfolio-level dashboard metrics."""
    distribution = {"Green": 0, "Yellow": 0, "Red": 0}
    total_open = 0
    total_high = 0
    for s in summaries:
        distribution[s["health"]] = distribution.get(s["health"], 0) + 1
        total_open += s["open_actions"]
        total_high += s["high_risks"]
    return {
        "project_count": len(summaries),
        "open_action_items": total_open,
        "high_risks": total_high,
        "health_distribution": distribution,
    }
