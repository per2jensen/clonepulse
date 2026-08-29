# SPDX-License-Identifier: MIT

"""Tests for abnormal clone filtering and JSON summary calculations."""

import pytest

from clonepulse.fetch_clones import build_summary, filter_abnormal_days


def _entry(day: int, count: int, uniques: int) -> dict[str, object]:
    """Create a UTC daily clone entry.

    Args:
        day: Day of January 2026.
        count: Clone count.
        uniques: Unique cloner count.

    Returns:
        A daily clone entry.

    Raises:
        ValueError: If the day is outside the test month.
    """
    if day < 1 or day > 31:
        raise ValueError("Test day must be between 1 and 31.")
    return {
        "timestamp": f"2026-01-{day:02d}T00:00:00Z",
        "count": count,
        "uniques": uniques,
    }


def test_filter_abnormal_days_above_threshold_imputes_preceding_normal_days() -> None:
    """Outliers are retained as raw data and receive a normal-day replacement."""
    source_entries = [
        _entry(1, 10, 2),
        _entry(2, 20, 4),
        _entry(3, 100, 2),
        _entry(4, 300, 0),
    ]

    filtered, discard = filter_abnormal_days(source_entries)

    assert "discarded" not in source_entries[2]
    assert filtered[2]["discarded"] is True
    assert filtered[2]["imputed_count"] == 15
    assert filtered[3]["imputed_count"] == 15
    assert discard[0]["ratio"] == 50.0
    assert discard[1]["ratio"] is None
    assert discard[1]["imputed_from_days"] == 2


def test_filter_abnormal_days_at_threshold_is_not_discarded() -> None:
    """A clone-to-unique ratio exactly equal to 25 remains valid."""
    filtered, discard = filter_abnormal_days([_entry(1, 500, 20)])

    assert discard == []
    assert filtered == [_entry(1, 500, 20)]


def test_filter_abnormal_days_invalid_entry_raises_value_error() -> None:
    """Malformed stored data fails before calculations begin."""
    with pytest.raises(ValueError, match="invalid count"):
        filter_abnormal_days([_entry(1, -1, 1)])


def test_filter_abnormal_days_invalid_configuration_raises_value_error() -> None:
    """Filtering rejects nonsensical threshold and window configuration."""
    with pytest.raises(ValueError, match="Ratio threshold"):
        filter_abnormal_days([], ratio_threshold=0)
    with pytest.raises(ValueError, match="Imputation window"):
        filter_abnormal_days([], impute_window=True)


def test_build_summary_reports_filtered_7_and_30_day_windows() -> None:
    """Summary windows exclude discarded days and expose their denominators."""
    entries = [_entry(day, day, day) for day in range(1, 31)]
    entries[27]["discarded"] = True
    entries[27]["imputed_count"] = 10

    summary = build_summary(entries, "2026-02-01T12:30:00Z")

    assert summary["total_clones"] == sum(range(1, 31)) - 28
    assert summary["unique_clones"] == sum(range(1, 31)) - 28
    assert summary["total_clones_raw"] == sum(range(1, 31))
    assert summary["last_7_days"] == {
        "total_clones": 161,
        "unique_clones": 161,
        "average_daily_clones": 26.83,
        "average_daily_unique_clones": 26.83,
        "days_included": 6,
        "days_discarded": 1,
    }
    assert summary["last_30_days"]["days_included"] == 29
    assert summary["last_30_days"]["days_discarded"] == 1
    assert summary["last_refresh"] == {
        "timestamp": "2026-02-01T12:30:00Z",
        "total_clones": 437,
        "unique_clones": 437,
    }


def test_build_summary_invalid_refresh_timestamp_raises_value_error() -> None:
    """A refresh snapshot cannot be created without an aware timestamp."""
    with pytest.raises(ValueError, match="timezone"):
        build_summary([], "2026-02-01T12:30:00")
