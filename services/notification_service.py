def build_alerts(
    forecast: dict | None,
    outliers: list[dict],
    duplicates: list[dict],
) -> list[dict]:
    alerts: list[dict] = []
    if forecast and forecast.get("cash_cliff_alert"):
        alerts.append({
            "type": "low_balance",
            "severity": "high",
            "message": (
                f"Projected balance in 30 days is ₹{forecast.get('projected_balance_day_30', 0):,.2f}, "
                "which is below the safety threshold."
            ),
        })
    for dup in duplicates:
        alerts.append({
            "type": "duplicate_charge",
            "severity": "medium",
            "message": (
                f"Possible duplicate: {dup.get('merchant')} for ₹{dup.get('amount'):,.2f} "
                f"within {dup.get('time_diff_seconds', 0):.0f}s."
            ),
        })
    for out in outliers:
        alerts.append({
            "type": "spending_outlier",
            "severity": "low",
            "message": (
                f"Unusual spending at {out.get('merchant')}: ₹{out.get('amount'):,.2f} "
                f"(Z-score: {out.get('z_score', 0):.1f})."
            ),
        })
    return alerts
