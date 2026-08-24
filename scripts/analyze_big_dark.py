"""Create the Washington Big Dark Index from downloaded daily weather data."""

from pathlib import Path
import sqlite3

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = PROJECT_ROOT / "data" / "raw" / "weather_daily_2006_2020.csv"
PROCESSED_DIRECTORY = PROJECT_ROOT / "data" / "processed"
SUMMARY_FILE = PROCESSED_DIRECTORY / "big_dark_summary.csv"
SQL_DIRECTORY = PROJECT_ROOT / "sql"
SQL_FILE = SQL_DIRECTORY / "winter_summary.sql"

FIRST_COMPLETE_WINTER = 2007
LAST_COMPLETE_WINTER = 2020
WET_DAY_THRESHOLD_MM = 1.0


SUMMARY_QUERY = """
SELECT
    community,
    region,
    AVG(requested_latitude) AS latitude,
    AVG(requested_longitude) AS longitude,
    AVG(daylight_hours) AS avg_daylight_hours,
    AVG(sunshine_hours) AS avg_sunshine_hours,
    AVG(sunshine_share) * 100 AS sunshine_share_pct,
    AVG(CASE WHEN precipitation_mm >= 1.0 THEN 1.0 ELSE 0.0 END) * 100
        AS wet_day_pct,
    SUM(precipitation_mm) / COUNT(DISTINCT winter_year)
        AS avg_winter_precipitation_mm,
    AVG(solar_energy_mj_m2) AS avg_solar_energy_mj_m2,
    COUNT(*) AS winter_day_records
FROM winter_weather
GROUP BY community, region
ORDER BY community;
""".strip()


def longest_true_streak(values):
    """Return the longest consecutive sequence of True values."""
    longest = 0
    current = 0

    for value in values:
        if value:
            current += 1
            longest = max(longest, current)
        else:
            current = 0

    return longest


def darker_when_lower(series):
    """Scale a measure from 0 to 1 when lower values mean a darker winter."""
    value_range = series.max() - series.min()
    if value_range == 0:
        return pd.Series(0.5, index=series.index)
    return (series.max() - series) / value_range


def darker_when_higher(series):
    """Scale a measure from 0 to 1 when higher values mean a darker winter."""
    value_range = series.max() - series.min()
    if value_range == 0:
        return pd.Series(0.5, index=series.index)
    return (series - series.min()) / value_range


def main():
    """Summarize complete winters, calculate scores, and save the ranking."""
    if not RAW_FILE.exists():
        raise FileNotFoundError(
            "Run scripts/download_weather.py before running this analysis."
        )

    weather = pd.read_csv(RAW_FILE, parse_dates=["date"])
    weather["winter_year"] = weather["year"]
    weather.loc[weather["month"] >= 11, "winter_year"] += 1

    winter = weather[
        weather["month"].isin([11, 12, 1, 2])
        & weather["winter_year"].between(
            FIRST_COMPLETE_WINTER, LAST_COMPLETE_WINTER
        )
    ].copy()

    winter["wet_day"] = winter["precipitation_mm"] >= WET_DAY_THRESHOLD_MM

    with sqlite3.connect(":memory:") as connection:
        winter.to_sql("winter_weather", connection, index=False, if_exists="replace")
        summary = pd.read_sql_query(SUMMARY_QUERY, connection)

    winter_streaks = (
        winter.sort_values("date")
        .groupby(["community", "winter_year"])["wet_day"]
        .apply(longest_true_streak)
        .reset_index(name="longest_wet_streak_days")
    )
    average_streaks = (
        winter_streaks.groupby("community", as_index=False)[
            "longest_wet_streak_days"
        ]
        .mean()
        .rename(
            columns={
                "longest_wet_streak_days": "avg_longest_wet_streak_days"
            }
        )
    )
    summary = summary.merge(average_streaks, on="community", how="left")

    summary["daylight_score"] = darker_when_lower(summary["avg_daylight_hours"])
    summary["sunshine_score"] = darker_when_lower(summary["avg_sunshine_hours"])
    summary["cloud_score"] = darker_when_lower(summary["sunshine_share_pct"])
    summary["wet_day_score"] = darker_when_higher(summary["wet_day_pct"])
    summary["precipitation_score"] = darker_when_higher(
        summary["avg_winter_precipitation_mm"]
    )

    component_columns = [
        "daylight_score",
        "sunshine_score",
        "cloud_score",
        "wet_day_score",
        "precipitation_score",
    ]
    summary["big_dark_index"] = summary[component_columns].mean(axis=1) * 100
    summary = summary.sort_values("big_dark_index", ascending=False).reset_index(
        drop=True
    )
    summary.insert(0, "rank", summary.index + 1)

    numeric_columns = summary.select_dtypes(include="number").columns
    summary[numeric_columns] = summary[numeric_columns].round(2)

    PROCESSED_DIRECTORY.mkdir(parents=True, exist_ok=True)
    SQL_DIRECTORY.mkdir(parents=True, exist_ok=True)
    summary.to_csv(SUMMARY_FILE, index=False)
    SQL_FILE.write_text(SUMMARY_QUERY + "\n", encoding="utf-8")

    display_columns = [
        "rank",
        "community",
        "big_dark_index",
        "avg_sunshine_hours",
        "wet_day_pct",
        "avg_winter_precipitation_mm",
    ]
    print(summary[display_columns].to_string(index=False))
    print("\nSaved summary to {}".format(SUMMARY_FILE))
    print("Saved SQL query to {}".format(SQL_FILE))


if __name__ == "__main__":
    main()
