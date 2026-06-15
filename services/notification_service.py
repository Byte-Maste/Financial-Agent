from schemas.models import ForecastReport, AnomalyReport


def build_alerts(
    forecast: ForecastReport | None,
    anomalies: AnomalyReport | None,
) -> list[dict]:
    alerts: list[dict] = []
    if forecast and forecast.cash_cliff_alert:
        alerts.append({
            "type": "low_balance",
            "severity": "high",
            "message": (
                f"Projected balance in 30 days is ₹{forecast.projected_balance_day_30:,.2f}, "
                "which is below the safety threshold."
            ),
        })
    if anomalies:
        for dup in anomalies.duplicates:
            alerts.append({
                "type": "duplicate_charge",
                "severity": "medium",
                "message": (
                    f"Possible duplicate: {dup.get('merchant')} for ₹{dup.get('amount'):,.2f} "
                    f"within {dup.get('time_diff_seconds', 0):.0f}s."
                ),
            })
        for out in anomalies.outliers:
            alerts.append({
                "type": "spending_outlier",
                "severity": "low",
                "message": (
                    f"Unusual spending at {out.get('merchant')}: ₹{out.get('amount'):,.2f} "
                    f"(Z-score: {out.get('z_score', 0):.1f})."
                ),
            })
    return alerts
