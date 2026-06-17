from fastapi import APIRouter

from services.pipeline_service import run_full_pipeline

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/dashboard/{user_id}")
async def get_dashboard(user_id: str):
    payload = await run_full_pipeline(user_id)
    analytics = payload.get("analytics", {})
    forecast = payload.get("forecast", {})
    budget_data = payload.get("budget", {})
    return {
        "financial_health_score": analytics.get("financial_health_score"),
        "savings_rate": analytics.get("savings_rate"),
        "emergency_fund_months": analytics.get("emergency_fund_months"),
        "monthly_savings": (
            budget_data.get("savings_actual") if budget_data else
            analytics.get("total_income", 0) - analytics.get("total_expenses", 0)
        ),
        "budget": {
            "needs_spent": budget_data.get("needs_spent"),
            "needs_target": budget_data.get("needs_target"),
            "wants_spent": budget_data.get("wants_spent"),
            "wants_target": budget_data.get("wants_target"),
            "savings_actual": budget_data.get("savings_actual"),
            "savings_target": budget_data.get("savings_target"),
        } if budget_data else None,
        "cash_flow_forecast": {
            "current_balance": forecast.get("current_balance"),
            "projected_balance_day_30": forecast.get("projected_balance_day_30"),
            "daily_balance": forecast.get("daily_balance", []),
        } if forecast else None,
        "fraud_alerts": [
            {"type": "outlier", "merchant": o.get("merchant"), "amount": o.get("amount")}
            for o in (payload.get("outliers") or [])
        ],
        "upcoming_bills": await _get_upcoming_bills(user_id),
        "active_alerts": payload.get("active_alerts", []),
    }


async def _get_upcoming_bills(user_id: str) -> list[dict]:
    from sqlalchemy import text
    from core.database import async_session_factory
    from datetime import date, timedelta
    async with async_session_factory() as session:
        rows = await session.execute(
            text(
                "SELECT DISTINCT merchant, amount, date FROM transactions "
                "WHERE user_id = :uid AND category = 'Bills' "
                "ORDER BY date DESC LIMIT 20"
            ),
            {"uid": user_id},
        )
        bills = []
        for r in rows.fetchall():
            last_date = r[2]
            due_in = (last_date.replace(year=last_date.year + (last_date.month // 12), month=(last_date.month % 12) + 1 or 1) - date.today()).days if last_date else None
            bills.append({
                "merchant": r[0],
                "amount": float(r[1]),
                "due_in_days": due_in if due_in and due_in > 0 else None,
            })
        return bills
