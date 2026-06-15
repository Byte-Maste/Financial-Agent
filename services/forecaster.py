import numpy as np
import pandas as pd

FORECAST_DAYS = 30
SAFETY_MARGIN_MULTIPLIER = 1


def forecast_cash_flow(
    current_balance: float,
    df: pd.DataFrame,
    fixed_commitments: list[float] | None = None,
) -> dict:
    fixed = fixed_commitments or []
    avg_daily_spend = _compute_daily_run_rate(df)
    daily_balance = [current_balance]
    for day in range(1, FORECAST_DAYS + 1):
        prev = daily_balance[-1]
        day_fixed = sum(fixed) / 30 if fixed else 0
        daily_outflow = avg_daily_spend + day_fixed
        daily_balance.append(round(prev - daily_outflow, 2))
    projected_end = daily_balance[-1]
    avg_monthly_expenses = df["amount"].sum() / max(len(df), 1) * 30 if not df.empty else 0
    cliff_alert = projected_end < (avg_monthly_expenses * SAFETY_MARGIN_MULTIPLIER)
    return {
        "current_balance": current_balance,
        "projected_balance_day_30": projected_end,
        "daily_run_rate": round(avg_daily_spend, 2),
        "daily_balance": daily_balance[1:],
        "cash_cliff_alert": cliff_alert,
    }


def _compute_daily_run_rate(df: pd.DataFrame) -> float:
    if df.empty:
        return 0
    date_range = (pd.to_datetime(df["date"]).max() - pd.to_datetime(df["date"]).min()).days
    date_range = max(date_range, 1)
    return float(df["amount"].sum()) / date_range
