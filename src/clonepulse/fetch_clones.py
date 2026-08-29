#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

""" 
Fetch clone data from GitHub API and update local JSON file,
triggered by Action `fetch_clones.json`.
The script retrieves clone statistics for the dar-backup repository
A badge on the repo README.md file will show the total number of clones.
Also, it will create a badge for each milestone reached (500, 1000, 2000 clones).
"""
import os
import json
import requests
import argparse
import logging
import re
from typing import Any
from urllib.parse import quote


from collections import OrderedDict
from datetime import datetime as dt
from datetime import timedelta, timezone
from clonepulse.util import show_scriptname
import clonepulse.__about__ as about

# Constants
CLONES_FILE = "clonepulse/fetch_clones.json"
MILESTONES = [500, 1000, 2000, 5000, 10000, 20000, 50000]
BADGE_DIR = "clonepulse"
BADGE_CLONES = "badge_clones.json"
RATIO_THRESHOLD = 25.0
IMPUTE_WINDOW = 7
SUMMARY_PERIODS = (7, 30)
REQUEST_TIMEOUT: tuple[float, float] = (5.0, 30.0)

LOGGER = logging.getLogger(__name__)


def filter_abnormal_days(
    entries: list[dict[str, Any]],
    ratio_threshold: float = RATIO_THRESHOLD,
    impute_window: int = IMPUTE_WINDOW,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Mark abnormal clone days and calculate replacement dashboard counts.

    Args:
        entries: Daily clone records from the stored history.
        ratio_threshold: Maximum accepted clone-to-unique-cloner ratio.
        impute_window: Maximum number of preceding normal days used for imputation.

    Returns:
        A tuple containing normalized daily entries and discard details.

    Raises:
        ValueError: If configuration or an entry is invalid.
    """
    if not isinstance(entries, list):
        raise ValueError("Daily clone entries must be a list.")
    if (
        not isinstance(ratio_threshold, (int, float))
        or isinstance(ratio_threshold, bool)
        or ratio_threshold <= 0
    ):
        raise ValueError("Ratio threshold must be greater than zero.")
    if (
        not isinstance(impute_window, int)
        or isinstance(impute_window, bool)
        or impute_window <= 0
    ):
        raise ValueError("Imputation window must be greater than zero.")

    normalized_records: list[tuple[dict[str, Any], dt]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"Daily entry {index} must be an object.")

        timestamp = entry.get("timestamp")
        count = entry.get("count")
        uniques = entry.get("uniques")
        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError(f"Daily entry {index} has an invalid timestamp: {timestamp!r}")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError(f"Daily entry {index} has an invalid count: {count!r}")
        if not isinstance(uniques, int) or isinstance(uniques, bool) or uniques < 0:
            raise ValueError(f"Daily entry {index} has invalid uniques: {uniques!r}")

        try:
            parsed_timestamp = dt.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(
                f"Daily entry {index} has an invalid timestamp: {timestamp!r}"
            ) from error
        if parsed_timestamp.tzinfo is None:
            raise ValueError(f"Daily entry {index} timestamp must include a timezone.")

        normalized_records.append(
            (
                {"timestamp": timestamp, "count": count, "uniques": uniques},
                parsed_timestamp,
            )
        )

    normalized_records.sort(key=lambda record: record[1])
    normalized_entries = [record[0] for record in normalized_records]
    entry_dates = [record[1].date().isoformat() for record in normalized_records]

    discarded_indexes = {
        index
        for index, entry in enumerate(normalized_entries)
        if (entry["uniques"] == 0 and entry["count"] > 0)
        or (
            entry["uniques"] > 0
            and entry["count"] / entry["uniques"] > ratio_threshold
        )
    }

    discard_details: list[dict[str, Any]] = []
    for index in sorted(discarded_indexes):
        entry = normalized_entries[index]
        preceding_counts: list[int] = []
        for previous_index in range(index - 1, -1, -1):
            if previous_index in discarded_indexes:
                continue
            preceding_counts.append(normalized_entries[previous_index]["count"])
            if len(preceding_counts) == impute_window:
                break

        imputed_count = (
            round(sum(preceding_counts) / len(preceding_counts))
            if preceding_counts
            else 0
        )
        entry["discarded"] = True
        entry["imputed_count"] = imputed_count

        uniques = entry["uniques"]
        ratio = round(entry["count"] / uniques, 1) if uniques > 0 else None
        ratio_text = f"{ratio}x" if ratio is not None else "N/A (zero uniques)"
        discard_reason = (
            f"Clone/unique ratio {ratio_text} exceeds threshold {ratio_threshold:g}x"
            if ratio is not None
            else "Positive clone count reported with zero unique cloners"
        )
        discard_details.append(
            {
                "date": entry_dates[index],
                "count": entry["count"],
                "uniques": uniques,
                "ratio": ratio,
                "imputed_count": imputed_count,
                "imputed_from_days": len(preceding_counts),
                "discard_reason": discard_reason,
            }
        )

    return normalized_entries, discard_details


def build_summary(
    entries: list[dict[str, Any]], refreshed_at: str
) -> dict[str, Any]:
    """Build lifetime, rolling-period, and refresh summary values.

    Args:
        entries: Normalized daily entries, including any discard markers.
        refreshed_at: UTC timestamp for the completed API refresh.

    Returns:
        Summary data ready for JSON serialization.

    Raises:
        ValueError: If entries or the refresh timestamp are invalid.
    """
    if not isinstance(entries, list):
        raise ValueError("Daily clone entries must be a list.")
    if not isinstance(refreshed_at, str) or not refreshed_at.strip():
        raise ValueError("Refresh timestamp must be a non-empty string.")

    try:
        refresh_time = dt.fromisoformat(refreshed_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"Invalid refresh timestamp: {refreshed_at!r}") from error
    if refresh_time.tzinfo is None:
        raise ValueError("Refresh timestamp must include a timezone.")

    dated_entries: list[tuple[dict[str, Any], dt]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"Daily entry {index} must be an object.")
        try:
            timestamp = entry["timestamp"]
            count = entry["count"]
            uniques = entry["uniques"]
        except KeyError as error:
            raise ValueError(f"Daily entry {index} is missing {error.args[0]!r}.") from error
        if not isinstance(timestamp, str):
            raise ValueError(f"Daily entry {index} has an invalid timestamp.")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError(f"Daily entry {index} has an invalid count.")
        if not isinstance(uniques, int) or isinstance(uniques, bool) or uniques < 0:
            raise ValueError(f"Daily entry {index} has invalid uniques.")
        try:
            entry_time = dt.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(
                f"Daily entry {index} has an invalid timestamp: {timestamp!r}"
            ) from error
        if entry_time.tzinfo is None:
            raise ValueError(f"Daily entry {index} timestamp must include a timezone.")
        dated_entries.append((entry, entry_time))

    for index, (entry, _) in enumerate(dated_entries):
        discarded = entry.get("discarded", False)
        if not isinstance(discarded, bool):
            raise ValueError(f"Daily entry {index} has an invalid discarded flag.")

    included_entries = [
        entry for entry, _ in dated_entries if not entry.get("discarded", False)
    ]
    total_clones = sum(entry["count"] for entry in included_entries)
    unique_clones = sum(entry["uniques"] for entry in included_entries)
    summary: dict[str, Any] = {
        "total_clones": total_clones,
        "unique_clones": unique_clones,
        "total_clones_raw": sum(entry["count"] for entry, _ in dated_entries),
    }

    newest_date = max(
        (entry_time.date() for _, entry_time in dated_entries), default=None
    )
    for period in SUMMARY_PERIODS:
        period_entries: list[dict[str, Any]] = []
        if newest_date is not None:
            first_date = newest_date - timedelta(days=period - 1)
            period_entries = [
                entry
                for entry, entry_time in dated_entries
                if first_date <= entry_time.date() <= newest_date
            ]

        included_period_entries = [
            entry for entry in period_entries if not entry.get("discarded", False)
        ]
        period_total = sum(entry["count"] for entry in included_period_entries)
        period_uniques = sum(entry["uniques"] for entry in included_period_entries)
        days_included = len(included_period_entries)
        summary[f"last_{period}_days"] = {
            "total_clones": period_total,
            "unique_clones": period_uniques,
            "average_daily_clones": (
                round(period_total / days_included, 2) if days_included else 0.0
            ),
            "average_daily_unique_clones": (
                round(period_uniques / days_included, 2) if days_included else 0.0
            ),
            "days_included": days_included,
            "days_discarded": len(period_entries) - days_included,
        }

    summary["last_refresh"] = {
        "timestamp": refreshed_at,
        "total_clones": total_clones,
        "unique_clones": unique_clones,
    }
    return summary



def validate_github_name(name: str, kind: str) -> str:
    if not name:
        raise argparse.ArgumentTypeError(f"{kind} name cannot be empty.")
    if len(name) > 100:
        raise argparse.ArgumentTypeError(f"{kind} name is too long.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise argparse.ArgumentTypeError(
            f"{kind} name '{name}' contains invalid characters. "
            "Only letters, numbers, hyphens (-), underscores (_), and dots (.) are allowed."
        )
    return name



def parse_args() -> argparse.Namespace:
    env_user = os.getenv("GITHUB_USER")
    env_repo = os.getenv("GITHUB_REPO")

    parser = argparse.ArgumentParser(
        description="Fetch GitHub clone stats for a given user and repo."
    )
    parser.add_argument(
        "--user",
        type=lambda x: validate_github_name(x, "GitHub user"),
        default=env_user,
        help="GitHub username/org (or set GITHUB_USER env var)"
    )
    parser.add_argument(
        "--repo",
        type=lambda x: validate_github_name(x, "GitHub repo"),
        default=env_repo,
        help="GitHub repository name (or set GITHUB_REPO env var)"
    )
    args = parser.parse_args()

    if not args.user:
        parser.error("GitHub user must be provided via --user or GITHUB_USER")
    if not args.repo:
        parser.error("GitHub repo must be provided via --repo or GITHUB_REPO")

    return args


def main() -> None:

    args = parse_args()
    print(f"{show_scriptname()} {about.__version__} running")
    print(f"Fetching data for repo: https://github.com/{args.user}/{args.repo}")


    # Load token from environment
    TOKEN = os.getenv("TOKEN")
    if not TOKEN:
        raise RuntimeError("TOKEN environment variable is not set. Please export your GitHub PAT as `TOKEN`.")
        
    HEADERS = {
        "Accept": "application/json",
        "Authorization": f"Bearer {TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28"
    }


    # Fetch clone data from GitHub API
    API_URL = f"https://api.github.com/repos/{quote(args.user)}/{quote(args.repo)}/traffic/clones"
    try:
        response = requests.get(
            API_URL,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        LOGGER.error(
            "GitHub clone API request failed for %s/%s: %s",
            args.user,
            args.repo,
            error,
        )
        raise RuntimeError(
            f"GitHub clone API request failed for {args.user}/{args.repo}."
        ) from error
    if not data.get("clones"):
        print("⚠️ No clone data returned from GitHub API.")
        exit(0)


    # --- Show raw API data debug info to stay in the CI log ---
    print("Raw clone data from GitHub API:")
    for day in data.get("clones", []):
        print(json.dumps(day, indent=2))


    # Load existing clone data if available
    if os.path.exists(CLONES_FILE):
        with open(CLONES_FILE, "r") as f:
            clones_data = json.load(f)
    else:
        clones_data = {
            "annotations": [],
            "daily": []
        }


    # Build existing entries as a dict (timestamp → entry)
    stored_entries, _ = filter_abnormal_days(clones_data.get("daily", []))
    existing_entries = {entry["timestamp"]: entry for entry in stored_entries}

    # Process and optionally update/skip each day's data
    for day in data.get("clones", []):
        try:
            timestamp = day["timestamp"]
            count = int(day["count"])
            uniques = int(day["uniques"])

            if count < 0 or uniques < 0:
                raise ValueError("Negative clone count")

            new_entry = {
                "timestamp": timestamp,
                "count": count,
                "uniques": uniques
            }
        except (KeyError, TypeError, ValueError) as e:
            print(f"⚠️ Skipping invalid entry: {day} ({e})")
            continue

        # Log if updated
        if timestamp in existing_entries:
            prev = existing_entries[timestamp]
            previous_values = {
                "timestamp": prev.get("timestamp"),
                "count": prev.get("count"),
                "uniques": prev.get("uniques"),
            }
            if previous_values != new_entry:
                print(f"🔄 Updated {timestamp}: {prev} → {new_entry}")

        existing_entries[timestamp] = new_entry

    daily_entries, discard_details = filter_abnormal_days(
        list(existing_entries.values())
    )
    clones_data["daily"] = daily_entries
    clones_data["discard"] = discard_details

    for detail in discard_details:
        ratio = detail["ratio"]
        ratio_text = f"{ratio}x" if ratio is not None else "N/A (zero uniques)"
        print(
            f"🚫 Discarding {detail['date']}: {detail['count']} clones, ratio "
            f"{ratio_text} → imputed {detail['imputed_count']} "
            f"(avg of {detail['imputed_from_days']} preceding days)"
        )
    if discard_details:
        print(
            f"⚠️  {len(discard_details)} day(s) discarded "
            f"(ratio > {RATIO_THRESHOLD:g}x)"
        )
    else:
        print(f"✅ No days discarded (ratio threshold: {RATIO_THRESHOLD:g}x)")

    refreshed_at = dt.now(timezone.utc).isoformat().replace("+00:00", "Z")
    summary = build_summary(daily_entries, refreshed_at)
    total_clones = summary["total_clones"]

    # --- Auto-annotate the true max non-discarded clone day ---
    valid_entries = [
        entry for entry in clones_data["daily"] if not entry.get("discarded", False)
    ]
    if valid_entries:
        # Step 1: Determine true max across all days
        max_entry = max(valid_entries, key=lambda d: d["count"])
        max_date = max_entry["timestamp"][:10]
        max_count = max_entry["count"]

        # Step 2: Remove all previous "max" annotations
        annotations = clones_data.setdefault("annotations", [])
        before = len(annotations)
        annotations[:] = [a for a in annotations if "max" not in a["label"].lower()]

        # Step 3: Add one correct max annotation
        annotations.append({
            "date": max_date,
            "label": f"Daily max: {max_count}"
        })
        print(f"📌 Set max annotation for {max_date}: {max_count} clones (replaced {before - len(annotations) + 1} old)")
    else:
        print("ℹ️ No valid (non-discarded) clone entries — skipping max annotation.")



    # Keep the summary at the top of the JSON document.
    ordered = OrderedDict()
    ordered["summary"] = summary
    if "annotations" in clones_data:
        ordered["annotations"] = clones_data["annotations"]
    ordered["discard"] = clones_data["discard"]
    ordered["daily"] = clones_data["daily"]


    # Save the updated file
    with open(CLONES_FILE + ".tmp", "w") as f:
        json.dump(ordered, f, indent=2)
    os.replace(CLONES_FILE + ".tmp", CLONES_FILE)


    # --- Milestone Watcher ---
    milestones_hit = []

    for milestone in MILESTONES:
        milestone_file = os.path.join(BADGE_DIR, f"milestone_{milestone}.txt")
        if total_clones >= milestone and not os.path.exists(milestone_file):
            with open(milestone_file, "w") as f:
                f.write(f"Reached {milestone} clones on {dt.now(timezone.utc).isoformat()}Z\n")
            milestones_hit.append(milestone)

    # Determine the highest milestone reached (if any)
    milestones_hit = [m for m in MILESTONES if total_clones >= m]


    # Optional: write a badge for the highest milestone reached
    if milestones_hit:
        last = milestones_hit[-1]

        # Convert milestone number into a compact label (1k+, 2k+, 5k+ ...)
        if last >= 1000:
            label = f"{last // 1000}k+ clones"
        else:
            # For 500 milestone
            label = f"{last}+ clones"
 
        print(f"🎯 Milestone reached: {label}")

        if last >= 2000:
            color = "red"
        elif last >= 1000:
            color = "orange"
        else:
            color = "goldenrod"

        badge = {
            "schemaVersion": 1,
            "label": "Milestone",
            "message": label,
            "color": color
        }
    else:
        badge = {
            "schemaVersion": 1,
            "label": "Milestone",
            "message": "Coming soon...",
            "color": "lightgray"
        }

    with open(os.path.join(BADGE_DIR, "milestone_badge.json"), "w") as f:
        json.dump(badge, f, indent=2)


    # --- Generate total clones badge.json ---
    badge = {
        "schemaVersion": 1,
        "label": "# clones",
        "message": str(total_clones),
        "color": "deeppink"
    }
    with open(os.path.join(BADGE_DIR, BADGE_CLONES), "w") as f:
        json.dump(badge, f, indent=2)



# Example use:
if __name__ == "__main__":
    main()
