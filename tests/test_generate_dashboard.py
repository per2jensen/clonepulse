# SPDX-License-Identifier: MIT

import os
import json
import tempfile
import shutil
from pathlib import Path
import pytest
import pandas as pd

# --- Helper ---
def write_test_json(path):
    """Creates valid input JSON with past dates only."""
    today = pd.Timestamp.now(tz="UTC").normalize()
    base = today - pd.Timedelta(days=14)
    daily = [
        {
            "timestamp": (base + pd.Timedelta(days=i)).isoformat(),
            "count": 10 + i,
            "uniques": 5 + i
        }
        for i in range(14)
    ]

    json_data = {
        "summary": {
            "total_clones": 999,
            "unique_clones": 500,
        },
        "annotations": [
            {"date": (base + pd.Timedelta(days=3)).strftime("%Y-%m-%d"), "label": "Some event"}
        ],
        "daily": daily
    }

    with open(path, "w") as f:
        json.dump(json_data, f)

def write_json_with_future_date(path):
    """Writes JSON with a future timestamp that should be rejected."""
    future_day = (
        pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=3)
    ).isoformat()
    daily = [{"timestamp": future_day, "count": 100, "uniques": 50}]
    with open(path, "w") as f:
        json.dump({"daily": daily}, f)

def test_rejects_future_timestamp(temp_env):
    import clonepulse.generate_clone_dashboard as dash
    write_json_with_future_date(dash.CLONES_FILE)
    with pytest.raises(ValueError, match=r"Row \d+ timestamp is in the future"):
        dash.main()

# --- Fixtures ---
@pytest.fixture
def temp_env():
    tempdir = tempfile.mkdtemp()
    import clonepulse.generate_clone_dashboard as dash
    dash.CLONES_FILE = os.path.join(tempdir, "fetch_clones.json")
    dash.OUTPUT_PNG = os.path.join(tempdir, "weekly_clones.png")
    yield tempdir
    shutil.rmtree(tempdir)

# --- Tests ---
def test_generate_dashboard_png(temp_env):
    import clonepulse.generate_clone_dashboard as dash
    write_test_json(dash.CLONES_FILE)
    dash.main()
    assert os.path.exists(dash.OUTPUT_PNG)

def test_rejects_future_timestamp(temp_env):
    import clonepulse.generate_clone_dashboard as dash
    write_json_with_future_date(dash.CLONES_FILE)
    with pytest.raises(ValueError, match="timestamp is in the future"):
        dash.main()

def test_insufficient_data_logged_and_skipped(temp_env, capsys):
    import clonepulse.generate_clone_dashboard as dash
    with open(dash.CLONES_FILE, "w") as f:
        json.dump({
            "daily": [
                {"timestamp": "2025-06-12T00:00:00Z", "count": 5, "uniques": 3},
                {"timestamp": "2025-06-13T00:00:00Z", "count": 6, "uniques": 3},
                {"timestamp": "2025-06-14T00:00:00Z", "count": 7, "uniques": 4},
                {"timestamp": "2025-06-15T00:00:00Z", "count": 8, "uniques": 5}
            ]
        }, f)

    dash.main()
    captured = capsys.readouterr()
    assert "Not enough daily data" in captured.out


def test_empty_dashboard_when_daily_missing(temp_env):
    import clonepulse.generate_clone_dashboard as dash
    # Write JSON with no 'daily' key
    with open(dash.CLONES_FILE, "w") as f:
        json.dump({}, f)

    dash.main()
    assert os.path.exists(dash.OUTPUT_PNG)



def test_empty_dashboard_when_daily_empty(temp_env):
    import clonepulse.generate_clone_dashboard as dash
    with open(dash.CLONES_FILE, "w") as f:
        json.dump({"daily": []}, f)

    dash.main()
    assert os.path.exists(dash.OUTPUT_PNG)


def test_empty_dashboard_when_not_enough_days(temp_env, capsys):
    import clonepulse.generate_clone_dashboard as dash
    with open(dash.CLONES_FILE, "w") as f:
        json.dump({
            "daily": [
                {"timestamp": "2025-06-01T00:00:00Z", "count": 4, "uniques": 2},
                {"timestamp": "2025-06-02T00:00:00Z", "count": 5, "uniques": 3}
            ]
        }, f)

    dash.main()
    captured = capsys.readouterr()
    assert os.path.exists(dash.OUTPUT_PNG)
    assert "Not enough daily data" in captured.out


def test_discarded_dashboard_days_are_imputed_or_skipped(temp_env, capsys):
    """Dashboard uses imputed clone counts and skips entries without replacements."""
    import clonepulse.generate_clone_dashboard as dash

    base = pd.Timestamp.now(tz="UTC").normalize() - pd.Timedelta(days=21)
    daily = [
        {
            "timestamp": (base + pd.Timedelta(days=index)).isoformat(),
            "count": 10,
            "uniques": 5,
        }
        for index in range(8)
    ]
    daily[0].update({"count": 500, "uniques": 1, "discarded": True})
    daily[1].update(
        {"count": 500, "uniques": 1, "discarded": True, "imputed_count": 10}
    )
    with open(dash.CLONES_FILE, "w") as file_handle:
        json.dump({"daily": daily}, file_handle)

    dash.main()

    captured = capsys.readouterr()
    assert "2 discarded day(s): 1 imputed, 1 skipped" in captured.out
    assert os.path.exists(dash.OUTPUT_PNG)


def test_invalid_discarded_flag_is_rejected(temp_env):
    """Dashboard rejects ambiguous discard marker values."""
    import clonepulse.generate_clone_dashboard as dash

    with open(dash.CLONES_FILE, "w") as file_handle:
        json.dump(
            {
                "daily": [
                    {
                        "timestamp": "2025-06-01T00:00:00Z",
                        "count": 10,
                        "uniques": 5,
                        "discarded": "yes",
                    }
                ]
            },
            file_handle,
        )

    with pytest.raises(ValueError, match="invalid discarded flag"):
        dash.main()
