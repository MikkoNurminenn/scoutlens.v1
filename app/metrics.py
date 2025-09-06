import numpy as np

def add_minutes_per_match(df):
    df["MinutesPerMatch"] = df["Minutes"] / df["Matches"].replace(0, np.nan)
    df["MinutesPerMatch"] = df["MinutesPerMatch"].replace([np.inf, -np.inf], np.nan).fillna(0)
    return df

def calculate_summary(df):
    return {
        "avg_age": round(df["Age"].mean(), 1) if not df.empty else 0,
        "avg_minutes": round(df["Minutes"].mean(), 1) if not df.empty else 0,
        "total_matches": int(df["Matches"].sum()) if not df.empty else 0,
        "avg_minutes_per_match": round(df["MinutesPerMatch"].mean(), 1) if not df.empty else 0,
    }