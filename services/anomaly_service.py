import numpy as np
import pandas as pd

Z_SCORE_THRESHOLD = 2.5
DUP_WINDOW_SECONDS = 60


def detect_outliers(df: pd.DataFrame) -> list[dict]:
    outliers: list[dict] = []
    for category, group in df.groupby("category"):
        if len(group) < 10:
            continue
        amounts = group["amount"].values
        mean = np.mean(amounts)
        std = np.std(amounts)
        if std == 0:
            continue
        z_scores = np.abs((amounts - mean) / std)
        for idx in np.where(z_scores > Z_SCORE_THRESHOLD)[0]:
            row = group.iloc[idx]
            outliers.append({
                "transaction_id": row.get("transaction_id", ""),
                "merchant": row.get("merchant", ""),
                "amount": float(row["amount"]),
                "date": str(row["date"]),
                "z_score": float(z_scores[idx]),
                "category": category,
            })
    return outliers


def detect_duplicates(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["date"])
    df = df.sort_values("datetime")
    duplicates: list[dict] = []
    for i in range(len(df) - 1):
        row_a = df.iloc[i]
        row_b = df.iloc[i + 1]
        time_diff = (row_b["datetime"] - row_a["datetime"]).total_seconds()
        if (
            row_a["merchant"] == row_b["merchant"]
            and abs(row_a["amount"] - row_b["amount"]) < 0.01
            and 0 < time_diff <= DUP_WINDOW_SECONDS
        ):
            duplicates.append({
                "transaction_id_a": row_a.get("transaction_id", ""),
                "transaction_id_b": row_b.get("transaction_id", ""),
                "merchant": row_a["merchant"],
                "amount": float(row_a["amount"]),
                "time_diff_seconds": time_diff,
            })
    return duplicates
