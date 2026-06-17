from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def persist_alerts(session: AsyncSession, user_id: str, alerts: list[dict]) -> None:
    for alert in alerts:
        await session.execute(
            text(
                "INSERT INTO alerts (user_id, type, severity, message) "
                "VALUES (:uid, :type, :severity, :message)"
            ),
            {
                "uid": user_id,
                "type": alert["type"],
                "severity": alert["severity"],
                "message": alert["message"],
            },
        )
    await session.commit()


async def get_unread_alerts(session: AsyncSession, user_id: str) -> list[dict]:
    rows = await session.execute(
        text("SELECT alert_id, type, severity, message, is_read, created_at "
             "FROM alerts WHERE user_id = :uid ORDER BY created_at DESC"),
        {"uid": user_id},
    )
    return [dict(r._mapping) for r in rows.fetchall()]


async def mark_alerts_read(session: AsyncSession, user_id: str, alert_ids: list[int]) -> None:
    await session.execute(
        text("UPDATE alerts SET is_read = TRUE WHERE user_id = :uid AND alert_id = ANY(:ids)"),
        {"uid": user_id, "ids": alert_ids},
    )
    await session.commit()


SAVINGS_RATE_TARGET = 0.20


def build_alerts(
    forecast: dict | None = None,
    outliers: list[dict] | None = None,
    duplicates: list[dict] | None = None,
    budget: dict | None = None,
    analytics: dict | None = None,
    inactive_subscriptions: list[dict] | None = None,
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
    for dup in (duplicates or []):
        alerts.append({
            "type": "duplicate_charge",
            "severity": "medium",
            "message": (
                f"Possible duplicate: {dup.get('merchant')} for ₹{dup.get('amount'):,.2f} "
                f"within {dup.get('time_diff_seconds', 0):.0f}s."
            ),
        })
    for out in (outliers or []):
        alerts.append({
            "type": "spending_outlier",
            "severity": "low",
            "message": (
                f"Unusual spending at {out.get('merchant')}: ₹{out.get('amount'):,.2f} "
                f"(Z-score: {out.get('z_score', 0):.1f})."
            ),
        })
    if budget:
        needs_pct = budget.get("needs_spent", 0) / max(budget.get("needs_target", 1), 1)
        wants_pct = budget.get("wants_spent", 0) / max(budget.get("wants_target", 1), 1)
        if needs_pct >= 0.9:
            alerts.append({
                "type": "budget_risk",
                "severity": "medium",
                "message": f"Needs spending is {needs_pct:.0%} of target — approaching budget limit.",
            })
        if wants_pct >= 0.9:
            alerts.append({
                "type": "budget_risk",
                "severity": "medium",
                "message": f"Wants spending is {wants_pct:.0%} of target — approaching budget limit.",
            })
    if analytics:
        rate = analytics.get("savings_rate", 1)
        if rate < SAVINGS_RATE_TARGET:
            alerts.append({
                "type": "savings_alert",
                "severity": "medium",
                "message": f"Savings rate is {rate:.0%}, below your {SAVINGS_RATE_TARGET:.0%} target.",
            })
    for sub in (inactive_subscriptions or []):
        alerts.append({
            "type": "subscription_alert",
            "severity": "low",
            "message": f"{sub.get('merchant')} subscription appears unused — consider cancelling.",
        })
    return alerts
