import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# [CRUX-MK]
# HINWEIS: `from 147 import ...` ist in Python-Syntax ungueltig.
# Fuer einen real gruennen pytest-Test wird das Modul daher per importlib geladen.

import importlib

m147 = importlib.import_module("147")

CustomerSnapshot = m147.CustomerSnapshot
build_nps_report = m147.build_nps_report
churn_risk_customers = m147.churn_risk_customers
onboarding_completion_rate = m147.onboarding_completion_rate
rolling_nps_score = m147.rolling_nps_score


def test_df_147_core_metrics():
    customers = [
        CustomerSnapshot(
            customer_id="cust-a",
            nps_responses=[10, 9],
            health_score=0.91,
            onboarding_steps_completed=5,
            onboarding_steps_total=5,
            has_open_critical_issue=False,
            days_since_last_activity=3,
        ),
        CustomerSnapshot(
            customer_id="cust-b",
            nps_responses=[6, 5],
            health_score=0.30,
            onboarding_steps_completed=1,
            onboarding_steps_total=4,
            has_open_critical_issue=True,
            days_since_last_activity=45,
        ),
        CustomerSnapshot(
            customer_id="cust-c",
            nps_responses=[8],
            health_score=0.62,
            onboarding_steps_completed=4,
            onboarding_steps_total=4,
            has_open_critical_issue=False,
            days_since_last_activity=10,
        ),
    ]

    assert rolling_nps_score([10, 9, 6, 5, 8]) == 0.0
    assert onboarding_completion_rate(customers) == 66.67
    assert churn_risk_customers(customers) == ["cust-b"]

    report = build_nps_report(customers, "2026-06-10")
    assert report == {
        "report_date": "2026-06-10",
        "rolling_nps_score": 0.0,
        "churn_risk_customers": ["cust-b"],
        "onboarding_completion_rate": 66.67,
        "auto_outreach_enabled": False,
    }


def test_empty_inputs_are_safe():
    assert rolling_nps_score([]) == 0.0
    assert onboarding_completion_rate([]) == 0.0
    assert churn_risk_customers([]) == []
    assert build_nps_report([], "2026-06-10")["auto_outreach_enabled"] is False

