from collections import defaultdict

import pandas as pd


def detect_recurring_charges(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    subscriptions: list[dict] = []
    grouped = df.groupby(["merchant", "amount"])
    for (merchant, amount), group in grouped:
        if len(group) < 2:
            continue
        dates = sorted(pd.to_datetime(group["date"]).tolist())
        intervals = []
        for i in range(1, len(dates)):
            delta = (dates[i] - dates[i - 1]).days
            intervals.append(delta)
        if not intervals:
            continue
        avg_interval = sum(intervals) / len(intervals)
        if 25 <= avg_interval <= 35:
            frequency = "monthly"
        elif 6 <= avg_interval <= 8:
            frequency = "weekly"
        elif 80 <= avg_interval <= 100:
            frequency = "quarterly"
        elif 350 <= avg_interval <= 380:
            frequency = "yearly"
        else:
            continue
        subscriptions.append({
            "merchant": merchant,
            "amount": float(amount),
            "frequency": frequency,
            "occurrences": len(group),
            "last_date": str(dates[-1].date()),
        })
    return subscriptions


def flag_inactive_subscriptions(
    subscriptions: list[dict], df: pd.DataFrame, lookback_days: int = 90
) -> list[dict]:
    if df.empty:
        return []
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=lookback_days)
    inactive: list[dict] = []
    for sub in subscriptions:
        merchant = sub["merchant"]
        recent = df[
            (df["merchant"] == merchant) & (pd.to_datetime(df["date"]) >= cutoff)
        ]
        if recent.empty:
            inactive.append({**sub, "reason": "no_usage_90_days"})
    return inactive
