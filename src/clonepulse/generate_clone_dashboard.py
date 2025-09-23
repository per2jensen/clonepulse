#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

"""
GitHub clone dashboard that aligns weekly totals to the following Monday.

Each data point on the chart represents the total clone activity from the
previous full week (Monday–Sunday), and is plotted on the following Monday.

This ensures that weekly metrics are only reported after a full week's data
has been collected. If the program is run mid-week, the current week's data
is excluded to avoid partial reporting.

If annotations are provided, they are displayed as vertical lines on the chart.
Annotations with "bad" dates (in the future or invalid) are skipped with a warning.
Annotations on the same date are stacked vertically to avoid overlap.

The script `fetch_clones.py` imports GitHub statistics into a JSON file, which
serves as input for this dashboard.

JSON Input Format:
------------------
{
  "total_clones": 845,
  "unique_clones": 418,
  "daily": [
    {
      "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
      "count": 30,
      "uniques": 15
    },
    ...
  ],
  "annotations": [
    {
      "date": "YYYY-MM-DD",
      "label": "Your label here"
    },
    ...
  ]
}

Validation Requirements:
------------------------
`daily`: required list of timestamp/count/uniques
`annotations`: optional list of date/label
"""

import os
import sys
import json
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from datetime import datetime
from clonepulse import __about__ as about
from clonepulse.util import show_scriptname

CLONES_FILE = "clonepulse/fetch_clones.json"
OUTPUT_PNG = "clonepulse/weekly_clones.png"
EMPTY_DASHBOARD_MESSAGE = "Not enough data to generate a dashboard.\nOne week's data needed."
NUM_WEEKS = 12  # Default weeks to display on the chart


def render_empty_dashboard(message: str):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.axis("off")
    ax.text(
        0.5, 0.5, message,
        ha="center", va="center",
        fontsize=14, color="gray",
        wrap=True, transform=ax.transAxes,
    )
    os.makedirs(os.path.dirname(OUTPUT_PNG), exist_ok=True)
    plt.savefig(OUTPUT_PNG)
    print("Empty dashboard generated (not enough data).")
    print(f"Output saved to: {OUTPUT_PNG}")


def _to_naive_utc_date(s: str) -> pd.Timestamp:
    return pd.to_datetime(s, utc=True).tz_convert(None).normalize()


def _utcnow_naive() -> pd.Timestamp:
    ts = pd.Timestamp.utcnow()
    return ts.tz_convert(None) if ts.tz is not None else ts


def _utc_today_naive() -> pd.Timestamp:
    ts = pd.Timestamp.utcnow()
    if ts.tz is not None:
        ts = ts.tz_convert(None)
    return ts.normalize()


def _truncate_on_word_boundary(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    words = text.split()
    out = []
    total = 0
    for w in words:
        add = len(w) if not out else len(w) + 1
        if total + add > max_chars - 3:
            break
        out.append(w)
        total += add
    if not out:
        return text[: max_chars - 3] + "..."
    return " ".join(out) + "..."


def main(argv=None):
    if argv is None:
        argv = []
    print(f"{show_scriptname()} {about.__version__} running")

    parser = argparse.ArgumentParser(description="Render GitHub clones weekly dashboard.")
    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help="Start reporting date (YYYY-MM-DD, typically a Monday). Window is inclusive.",
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=NUM_WEEKS,
        help=f"Number of weeks to display (default: {NUM_WEEKS}).",
    )
    parser.add_argument(
        "--year",
        type=str,
        default=None,
        help="Calendar year to plot (YYYY). Overrides --start and --weeks.",
    )
    args = parser.parse_args(argv)

    if args.weeks is not None and int(args.weeks) < 0:
        print(f"ERROR: --weeks must be non-negative. Got {args.weeks}.", file=sys.stderr)
        sys.exit(2)
    weeks_to_plot = int(args.weeks)

    try:
        with open(CLONES_FILE, "r") as f:
            clones_data = json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load or parse JSON file: {e}")

    raw_rows = clones_data.get("daily", [])
    if not raw_rows or not isinstance(raw_rows, list):
        render_empty_dashboard(EMPTY_DASHBOARD_MESSAGE)
        return

    validated_rows = []
    now_ts = _utcnow_naive()
    for i, row in enumerate(raw_rows):
        try:
            ts = pd.to_datetime(row["timestamp"], utc=True)
        except Exception:
            raise ValueError(f"Row {i} has invalid timestamp: {row.get('timestamp')}")
        if ts.tz_convert(None) > now_ts:
            raise ValueError(f"Row {i} timestamp is in the future: {ts}")

        count = row.get("count")
        uniques = row.get("uniques")
        if not isinstance(count, int) or count < 0:
            raise ValueError(f"Row {i} has invalid count: {count}")
        if not isinstance(uniques, int) or uniques < 0:
            raise ValueError(f"Row {i} has invalid uniques: {uniques}")

        validated_rows.append({"timestamp": ts, "count": count, "uniques": uniques})

    df = pd.DataFrame(validated_rows)
    if df.shape[0] < 7:
        render_empty_dashboard(EMPTY_DASHBOARD_MESSAGE)
        print(f"⚠️ Not enough daily data to generate a weekly chart ({df.shape[0]} days).")
        return

    df["timestamp"] = df["timestamp"].dt.tz_convert(None)
    now_naive = _utcnow_naive()
    df = df[df["timestamp"] <= now_naive]

    df["week_start"] = df["timestamp"] - pd.to_timedelta(df["timestamp"].dt.weekday, unit="D")
    df["week_start"] = df["week_start"].dt.normalize()

    if df.empty:
        print("No valid clone data available.")
        render_empty_dashboard(EMPTY_DASHBOARD_MESSAGE)
        return

    weekly_data = df.groupby("week_start")[["count", "uniques"]].sum().reset_index()

    if weekly_data.empty:
        print("⚠️ Weekly data is empty after aggregation. Nothing to plot.")
        render_empty_dashboard(EMPTY_DASHBOARD_MESSAGE)
        return

    today = _utc_today_naive()
    weekly_data = weekly_data[weekly_data["week_start"] + pd.Timedelta(days=6) < today]

    if weekly_data.empty:
        print("⚠️ Weekly data is empty after excluding current week.")
        render_empty_dashboard(EMPTY_DASHBOARD_MESSAGE)
        return

    weekly_data["count_avg"] = weekly_data["count"].rolling(window=3, min_periods=1).mean()
    weekly_data["uniques_avg"] = weekly_data["uniques"].rolling(window=3, min_periods=1).mean()
    weekly_data["report_date"] = weekly_data["week_start"] + pd.Timedelta(days=7)
    weekly_data = weekly_data.sort_values("report_date").reset_index(drop=True)

    # --- Year filter ---
    if args.year:
        year_str = args.year.strip()
        if len(year_str) != 4 or not year_str.isdigit():
            print(f"ERROR: --year must be in YYYY format. Got {args.year!r}.", file=sys.stderr)
            sys.exit(2)
        year = int(year_str)

        today_naive = _utc_today_naive()
        if year > today_naive.year:
            print(f"ERROR: --year is in the future: {year}.", file=sys.stderr)
            sys.exit(2)

        year_start = pd.Timestamp(year=year, month=1, day=1)
        year_end = pd.Timestamp(year=year, month=12, day=31)

        year_data = weekly_data[
            (weekly_data["week_start"] >= year_start) &
            (weekly_data["week_start"] <= year_end)
        ].copy()

        if year_data.empty:
            render_empty_dashboard(f"No data for year {year}.")
            print(f"⚠️ No weekly data found for {year}. Empty dashboard produced.")
            return

        weekly_data = year_data
        plot_start = weekly_data["report_date"].min().normalize()
        plot_end = weekly_data["report_date"].max().normalize()
    else:
        if args.start:
            try:
                plot_start = _to_naive_utc_date(args.start)
            except Exception:
                raise ValueError(f"Invalid --start date: {args.start!r}")
            if plot_start > _utc_today_naive():
                print(f"ERROR: --start date is in the future: {args.start}", file=sys.stderr)
                sys.exit(2)

            plot_end = plot_start + pd.Timedelta(weeks=max(weeks_to_plot - 1, 0))
            weekly_data = weekly_data[
                (weekly_data["report_date"] >= plot_start) &
                (weekly_data["report_date"] <= plot_end)
            ]
        else:
            weekly_data = weekly_data.tail(weeks_to_plot)
            if not weekly_data.empty:
                plot_start = weekly_data["report_date"].min().normalize()
                plot_end = weekly_data["report_date"].max().normalize()
            else:
                plot_start = plot_end = None

        if weekly_data.empty or plot_start is None:
            print("⚠️ No weekly data in the selected window.")
            render_empty_dashboard("No data in the selected window.")
            return

    annotations = clones_data.get("annotations", [])
    valid_annotations = []
    now_norm = _utc_today_naive()

    if not isinstance(annotations, list):
        print("⚠️  'annotations' field is not a list — skipping all annotations.")
    else:
        for i, ann in enumerate(annotations):
            if not isinstance(ann, dict):
                print(f"⚠️  Annotation {i} is not a dict — skipping.")
                continue
            if not {"date", "label"}.issubset(ann):
                print(f"⚠️  Annotation {i} missing 'date' or 'label' — skipping.")
                continue
            try:
                ann_date = _to_naive_utc_date(ann["date"])
                if ann_date > now_norm:
                    print(f"⚠️  Annotation {i} has future date ({ann['date']}) — skipping.")
                    continue
            except Exception:
                print(f"⚠️  Annotation {i} has invalid date format — skipping.")
                continue
            label = ann["label"]
            if not isinstance(label, str):
                print(f"⚠️  Annotation {i} label is not a string — skipping.")
                continue
            valid_annotations.append({"date": ann_date, "label": label})

    annotation_df = pd.DataFrame(valid_annotations).sort_values("date")

    if not annotation_df.empty:
        in_window = (annotation_df["date"] >= plot_start) & (annotation_df["date"] <= plot_end)
        dropped = int((~in_window).sum())
        if dropped:
            print(f"ℹ️  Skipping {dropped} annotation(s) outside [{plot_start.date()} .. {plot_end.date()}].")
        annotation_df = annotation_df.loc[in_window].reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(weekly_data["report_date"], weekly_data["count"], label="Total Clones", marker="o")
    ax.plot(weekly_data["report_date"], weekly_data["count_avg"], label="Total Clones (3w Avg)", linestyle="--")
    ax.plot(weekly_data["report_date"], weekly_data["uniques"], label="Unique Clones", marker="s")
    ax.plot(weekly_data["report_date"], weekly_data["uniques_avg"], label="Unique Clones (3w Avg)", linestyle=":")

    fig_height_px = fig.get_size_inches()[1] * fig.dpi
    max_vertical_pixels = fig_height_px / 3
    pixels_per_char = 8
    max_chars = int(max_vertical_pixels // pixels_per_char)
    print(f"Max annotation label characters allowed: {max_chars}")

    ymin, ymax = ax.get_ylim()
    label_y = ymin + 0.97 * (ymax - ymin)
    offset_step_pts = 12

    if not annotation_df.empty:
        for ann_date, group in annotation_df.groupby("date", sort=True):
            ax.axvline(x=ann_date, color="gray", linestyle=":", linewidth=1)
            for i, (_, row) in enumerate(group.iterrows()):
                label = _truncate_on_word_boundary(row["label"], max_chars)
                ax.annotate(
                    label,
                    xy=(ann_date, label_y),
                    xytext=(0, -5 - i * offset_step_pts),
                    textcoords="offset points",
                    rotation=90,
                    fontsize=10,
                    ha="center",
                    va="top",
                    color="dimgray",
                    clip_on=True,
                )

    ax.set_title("Weekly Clone Metrics (Reported on Following Monday)")
    ax.set_xlabel("Reporting Date (Monday after week ends)")
    ax.set_ylabel("Clones")
    ax.grid(True)

    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    tick_dates = pd.to_datetime(weekly_data["report_date"], errors="coerce")
    tick_labels = tick_dates.dt.strftime("%Y-%m-%d").fillna("Invalid")
    ax.set_xticks(tick_dates.to_list())
    ax.set_xticklabels(tick_labels.to_list(), rotation=45)

    ax.legend(loc="lower left", fontsize=9)
    plt.tight_layout()

    os.makedirs(os.path.dirname(OUTPUT_PNG), exist_ok=True)
    plt.savefig(OUTPUT_PNG)

    print(f"✅ Dashboard rendered with {len(weekly_data)} weeks.")
    last_week = weekly_data.iloc[-1]
    start_date = last_week["week_start"].date()
    end_date = (last_week["week_start"] + pd.Timedelta(days=6)).date()
    report_date = last_week["report_date"].date()
    print(f"📊 Latest week: {start_date} → {end_date} (reported on {report_date})")
    print(f"🖼️  Output saved to: {OUTPUT_PNG}")


if __name__ == "__main__":
    main(sys.argv[1:])
