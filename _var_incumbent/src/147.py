from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class CustomerSnapshot:
    customer_id: str
    nps_responses: List[int]
    health_score: float
    onboarding_steps_completed: int
    onboarding_steps_total: int
    has_open_critical_issue: bool = False
    days_since_last_activity: Optional[int] = None


def rolling_nps_score(scores: Iterable[int]) -> float:
    values = list(scores)
    if not values:
        return 0.0

    promoters = sum(1 for s in values if s >= 9)
    detractors = sum(1 for s in values if s <= 6)
    total = len(values)
    return round(((promoters - detractors) / total) * 100, 2)


def onboarding_completion_rate(customers: Iterable[CustomerSnapshot]) -> float:
    items = list(customers)
    if not items:
        return 0.0

    completed = 0
    for c in items:
        if c.onboarding_steps_total > 0 and c.onboarding_steps_completed >= c.onboarding_steps_total:
            completed += 1

    return round((completed / len(items)) * 100, 2)


def churn_risk_customers(customers: Iterable[CustomerSnapshot]) -> List[str]:
    risky: List[str] = []

    for c in customers:
        avg_nps = mean(c.nps_responses) if c.nps_responses else 7.0
        low_nps = avg_nps <= 6.0
        low_health = c.health_score < 0.45
        inactive = c.days_since_last_activity is not None and c.days_since_last_activity >= 30
        onboarding_stalled = (
            c.onboarding_steps_total > 0
            and (c.onboarding_steps_completed / c.onboarding_steps_total) < 0.5
        )

        risk_signals = sum(
            [low_nps, low_health, c.has_open_critical_issue, inactive, onboarding_stalled]
        )
        if risk_signals >= 2:
            risky.append(c.customer_id)

    return sorted(risky)


def build_nps_report(
    customers: Iterable[Dict[str, Any] | CustomerSnapshot],
    report_date: str,
) -> Dict[str, Any]:
    snapshots: List[CustomerSnapshot] = []
    for item in customers:
        if isinstance(item, CustomerSnapshot):
            snapshots.append(item)
        else:
            snapshots.append(CustomerSnapshot(**item))

    all_scores: List[int] = []
    for c in snapshots:
        all_scores.extend(c.nps_responses)

    return {
        "report_date": report_date,
        "rolling_nps_score": rolling_nps_score(all_scores),
        "churn_risk_customers": churn_risk_customers(snapshots),
        "onboarding_completion_rate": onboarding_completion_rate(snapshots),
        "auto_outreach_enabled": False,
    }


__all__ = [
    "CustomerSnapshot",
    "rolling_nps_score",
    "onboarding_completion_rate",
    "churn_risk_customers",
    "build_nps_report",
]
# [CRUX-MK]
