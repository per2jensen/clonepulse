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
    today = pd.Timestamp.utcnow().normalize()
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
        "annotations": [
            {"date": (base + pd.Timedelta(days=3)).strftime("%Y-%m-%d"), "label": "Some event"}
        ],
        "total_clones": 999,
        "unique_clones": 500,
        "daily": daily
    }

    with open(path, "w") as f:
        json.dump(json_data, f)

def write_json_with_future_date(path):
    """Writes JSON with a future timestamp that should be rejected."""
    future_day = (pd.Timestamp.utcnow() + pd.Timedelta(days=3)).isoformat()
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
