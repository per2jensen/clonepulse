# SPDX-License-Identifier: MIT

import argparse
import clonepulse.fetch_clones as fc
import json
import os
import os
import pytest
import pytest
import shutil
import tempfile


from clonepulse.fetch_clones import validate_github_name, parse_args
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock



# --- Tests for validate_github_name ---
@pytest.mark.parametrize("name", ["octocat", "user-123", "org.name", "repo_name"])
def test_validate_github_name_valid(name):
    assert validate_github_name(name, "GitHub user") == name

@pytest.mark.parametrize("name", ["", "user with space", "bad!char", "a"*101])
def test_validate_github_name_invalid(name):
    with pytest.raises(argparse.ArgumentTypeError):
        validate_github_name(name, "GitHub user")

# --- Tests for parse_args ---
def test_parse_args_from_env(monkeypatch):
    monkeypatch.setenv("GITHUB_USER", "octocat")
    monkeypatch.setenv("GITHUB_REPO", "hello-world")

    # Empty sys.argv to simulate no --user or --repo
    monkeypatch.setattr("sys.argv", ["script_name"])
    args = parse_args()
    assert args.user == "octocat"
    assert args.repo == "hello-world"

def test_parse_args_from_cli(monkeypatch):
    monkeypatch.delenv("GITHUB_USER", raising=False)
    monkeypatch.delenv("GITHUB_REPO", raising=False)

    monkeypatch.setattr("sys.argv", ["script_name", "--user", "octocat", "--repo", "hello-world"])
    args = parse_args()
    assert args.user == "octocat"
    assert args.repo == "hello-world"



@pytest.fixture
def temp_badges_dir():
    """Create a temporary badges dir and override constants."""
    orig_clones_file = fc.CLONES_FILE
    orig_badge_dir = fc.BADGE_DIR
    orig_badge_clones = fc.BADGE_CLONES

    tmpdir = tempfile.mkdtemp()
    fc.CLONES_FILE = os.path.join(tmpdir, "fetch_clones.json")
    fc.BADGE_DIR = tmpdir
    fc.BADGE_CLONES = "badge_clones.json"

    yield tmpdir

    # Cleanup and restore constants
    shutil.rmtree(tmpdir)
    fc.CLONES_FILE = orig_clones_file
    fc.BADGE_DIR = orig_badge_dir
    fc.BADGE_CLONES = orig_badge_clones


def mock_api_response():
    return {
        "clones": [
            {"timestamp": "2024-06-01T00:00:00Z", "count": 10, "uniques": 5},
            {"timestamp": "2024-06-02T00:00:00Z", "count": 20, "uniques": 8},
        ]
    }


@mock.patch("clonepulse.fetch_clones.requests.get")
@mock.patch("clonepulse.fetch_clones.parse_args")
def test_fetch_clones_end_to_end(mock_parse_args, mock_get, temp_badges_dir):
    # Setup mock API response
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = mock_api_response()

    # Provide dummy args and token
    mock_parse_args.return_value.user = "dummy-user"
    mock_parse_args.return_value.repo = "dummy-repo"
    os.environ["TOKEN"] = "fake-token"

    # Run main logic
    fc.main()

    # Check fetch_clones.json was created and values correct
    clones_file = Path(fc.CLONES_FILE)
    assert clones_file.exists()

    with clones_file.open() as f:
        data = json.load(f)

    assert data["total_clones"] == 30
    assert data["unique_clones"] == 13
    assert any("Daily max" in a["label"] for a in data["annotations"])

    # Check badge_clones.json
    badge_file = Path(temp_badges_dir) / "badge_clones.json"
    assert badge_file.exists()
    badge = json.loads(badge_file.read_text())
    assert badge["label"] == "# clones"
    assert badge["message"] == "30"

    # Check milestone_badge.json
    milestone_file = Path(temp_badges_dir) / "milestone_badge.json"
    assert milestone_file.exists()
    milestone = json.loads(milestone_file.read_text())

    # Should be below first milestone
    assert milestone["message"] == "Coming soon..."

    # Trigger again with >500 total clones to test milestone badge
    mock_get.return_value.json.return_value["clones"].append(
        {"timestamp": "2024-06-03T00:00:00Z", "count": 500, "uniques": 10}
    )
    fc.main()

    updated = json.loads(badge_file.read_text())
    assert updated["message"] == "530"

    milestone = json.loads(milestone_file.read_text())
    assert milestone["message"] == "500+ clones"


def test_missing_token(monkeypatch):
    monkeypatch.delenv("TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_USER", "octocat")
    monkeypatch.setenv("GITHUB_REPO", "hello-world")

    # Ensure argparse doesn't see pytest args
    monkeypatch.setattr("sys.argv", ["script_name"])

    with pytest.raises(RuntimeError, match="TOKEN environment variable is not set"):
        fc.main()


@mock.patch("clonepulse.fetch_clones.requests.get")
@mock.patch("clonepulse.fetch_clones.parse_args")
def test_api_error_response(mock_parse_args, mock_get):
    mock_get.return_value.status_code = 403
    mock_get.return_value.raise_for_status.side_effect = Exception("403 Forbidden")

    mock_parse_args.return_value.user = "user"
    mock_parse_args.return_value.repo = "repo"
    os.environ["TOKEN"] = "fake-token"

    with pytest.raises(Exception, match="403 Forbidden"):
        fc.main()



@mock.patch("clonepulse.fetch_clones.requests.get")
@mock.patch("clonepulse.fetch_clones.parse_args")
def test_no_clones_key(mock_parse_args, mock_get, capsys):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {}

    mock_parse_args.return_value.user = "user"
    mock_parse_args.return_value.repo = "repo"
    os.environ["TOKEN"] = "fake-token"

    with pytest.raises(SystemExit):
        fc.main()

    captured = capsys.readouterr()
    assert "⚠️ No clone data returned" in captured.out


import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest import mock
import pytest
import clonepulse.fetch_clones as fc

@pytest.fixture
def temp_badges_dir():
    """Create a temporary badges dir and override constants."""
    orig_clones_file = fc.CLONES_FILE
    orig_badge_dir = fc.BADGE_DIR
    orig_badge_clones = fc.BADGE_CLONES

    tmpdir = tempfile.mkdtemp()
    fc.CLONES_FILE = os.path.join(tmpdir, "fetch_clones.json")
    fc.BADGE_DIR = tmpdir
    fc.BADGE_CLONES = "badge_clones.json"

    yield tmpdir

    # Cleanup and restore constants
    shutil.rmtree(tmpdir)
    fc.CLONES_FILE = orig_clones_file
    fc.BADGE_DIR = orig_badge_dir
    fc.BADGE_CLONES = orig_badge_clones


@mock.patch("clonepulse.fetch_clones.requests.get")
@mock.patch("clonepulse.fetch_clones.parse_args")
def test_malformed_clone_entry_skipped(mock_parse_args, mock_get, temp_badges_dir, capsys):
    # Simulate malformed API data (count is a string)
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "clones": [
            {"timestamp": "2024-06-01T00:00:00Z", "count": "not-a-number", "uniques": 10}
        ]
    }

    # Setup minimal viable env
    mock_parse_args.return_value.user = "user"
    mock_parse_args.return_value.repo = "repo"
    os.environ["TOKEN"] = "fake-token"

    # Run main
    fc.main()

    # Capture printed output and verify it skipped the bad entry
    captured = capsys.readouterr()
    assert "⚠️ Skipping invalid entry" in captured.out

    # Check that fetch_clones.json exists and daily is empty
    clones_file = Path(fc.CLONES_FILE)
    assert clones_file.exists()
    with clones_file.open() as f:
        data = json.load(f)

    assert data["daily"] == []
    assert data["total_clones"] == 0
    assert data["unique_clones"] == 0
    assert data.get("annotations") == []

    # Check that badge files still exist with default values
    badge_clones = Path(temp_badges_dir) / "badge_clones.json"
    assert badge_clones.exists()
    badge = json.loads(badge_clones.read_text())
    assert badge["message"] == "0"

    milestone_badge = Path(temp_badges_dir) / "milestone_badge.json"
    assert milestone_badge.exists()
    milestone = json.loads(milestone_badge.read_text())
    assert milestone["message"] == "Coming soon..."


@mock.patch("clonepulse.fetch_clones.requests.get")
@mock.patch("clonepulse.fetch_clones.parse_args")
def test_max_annotation_updates_when_new_peak_arrives(mock_parse_args, mock_get, temp_badges_dir):
    """
    Verifies that when a new higher max 'count' appears, the script
    replaces the previous 'Daily max: ...' annotation with the new one.
    """
    # Initial API payload with lower max (20 on 2024-06-02)
    resp = {
        "clones": [
            {"timestamp": "2024-06-01T00:00:00Z", "count": 10, "uniques": 5},
            {"timestamp": "2024-06-02T00:00:00Z", "count": 20, "uniques": 8},
        ]
    }
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = resp
    mock_parse_args.return_value.user = "user"
    mock_parse_args.return_value.repo = "repo"
    os.environ["TOKEN"] = "fake-token"
    # First run → max=20 on 2024-06-02
    fc.main()
    with open(fc.CLONES_FILE) as fh:
        data1 = json.load(fh)
    ann1 = [a for a in data1.get("annotations", []) if "daily max" in a["label"].lower()]
    assert len(ann1) == 1
    assert ann1[0]["date"] == "2024-06-02"
    assert ann1[0]["label"] == "Daily max: 20"
    # Second run with a new higher max (999 on 2024-06-03)
    resp["clones"].append({"timestamp": "2024-06-03T00:00:00Z", "count": 999, "uniques": 10})
    mock_get.return_value.json.return_value = resp
    fc.main()
    with open(fc.CLONES_FILE) as fh:
        data2 = json.load(fh)
    ann2 = [a for a in data2.get("annotations", []) if "daily max" in a["label"].lower()]
    assert len(ann2) == 1, "There should be exactly one max annotation after replacement"
    assert ann2[0]["date"] == "2024-06-03"
    assert ann2[0]["label"] == "Daily max: 999"


@mock.patch("clonepulse.fetch_clones.requests.get")
@mock.patch("clonepulse.fetch_clones.parse_args")
def test_idempotent_merge_produces_stable_json(mock_parse_args, mock_get, temp_badges_dir):
    """
    Running the fetcher twice with the exact same API payload should
    produce identical JSON output (no duplicate days, stable annotations).
    """
    api_payload = {
        "clones": [
            {"timestamp": "2024-06-10T00:00:00Z", "count": 7, "uniques": 3},
            {"timestamp": "2024-06-11T00:00:00Z", "count": 9, "uniques": 4},
        ]
    }
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = api_payload
    mock_parse_args.return_value.user = "user"
    mock_parse_args.return_value.repo = "repo"
    os.environ["TOKEN"] = "fake-token"
    # First run
    fc.main()
    json_v1 = Path(fc.CLONES_FILE).read_text()
    # Second run with the same payload
    fc.main()
    json_v2 = Path(fc.CLONES_FILE).read_text()
    assert json_v1 == json_v2, "JSON output must be stable across identical runs"
    data = json.loads(json_v2)
    assert len(data["daily"]) == 2
    assert data["total_clones"] == 16
    assert data["unique_clones"] == 7



@mock.patch("clonepulse.fetch_clones.requests.get")
@mock.patch("clonepulse.fetch_clones.parse_args")
def test_milestone_badge_colors_progression(mock_parse_args, mock_get, temp_badges_dir):
    """
    As totals cross 500, 1000, 2000, the milestone badge color should progress:
      - >=500  -> goldenrod
      - >=1000 -> orange
      - >=2000 -> red
    """
    mock_parse_args.return_value.user = "user"
    mock_parse_args.return_value.repo = "repo"
    os.environ["TOKEN"] = "fake-token"
    badge_path = Path(temp_badges_dir) / "milestone_badge.json"
    # Hit 500 (goldenrod)
    resp = {
        "clones": [
            {"timestamp": "2024-06-01T00:00:00Z", "count": 500, "uniques": 100},
        ]
    }
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = resp
    fc.main()
    badge = json.loads(badge_path.read_text())
    assert badge["message"] == "500+ clones"
    assert badge["color"] == "goldenrod"
    # Hit 1000 (orange) by adding another 500
    resp["clones"].append({"timestamp": "2024-06-02T00:00:00Z", "count": 500, "uniques": 80})
    mock_get.return_value.json.return_value = resp
    fc.main()
    badge = json.loads(badge_path.read_text())
    assert badge["message"] == "1k+ clones"
    assert badge["color"] == "orange"
    # Hit 2000 (red) by adding another 1000
    resp["clones"].append({"timestamp": "2024-06-03T00:00:00Z", "count": 1000, "uniques": 120})
    mock_get.return_value.json.return_value = resp
    fc.main()
    badge = json.loads(badge_path.read_text())
    assert badge["message"] == "2k+ clones"
    assert badge["color"] == "red"



@mock.patch("clonepulse.fetch_clones.requests.get")
@mock.patch("clonepulse.fetch_clones.parse_args")
def test_max_annotation_stable_when_only_nonmax_days_change(mock_parse_args, mock_get, temp_badges_dir):
    """
    The 'Daily max: ...' annotation must remain stable when updates only affect
    non-max days. We start with a clear max on 2024-06-02 (count=50), then
    increase 2024-06-01 from 10 -> 40 (< 50). The max annotation should not change.
    """
    # --- Initial payload: max at 2024-06-02 (50) ---
    resp = {
        "clones": [
            {"timestamp": "2024-06-01T00:00:00Z", "count": 10, "uniques": 5},
            {"timestamp": "2024-06-02T00:00:00Z", "count": 50, "uniques": 20},  # global max
            {"timestamp": "2024-06-03T00:00:00Z", "count": 12, "uniques": 7},
        ]
    }
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = resp
    mock_parse_args.return_value.user = "user"
    mock_parse_args.return_value.repo = "repo"
    os.environ["TOKEN"] = "fake-token"
    # Run 1: establish baseline max annotation (2024-06-02 -> 50)
    fc.main()
    with open(fc.CLONES_FILE) as fh:
        data_before = json.load(fh)
    max_anns_before = [a for a in data_before.get("annotations", []) if "daily max" in a["label"].lower()]
    assert len(max_anns_before) == 1, "There should be a single max annotation after first run"
    assert max_anns_before[0]["date"] == "2024-06-02"
    assert max_anns_before[0]["label"] == "Daily max: 50"
    # --- Update a NON-MAX day only (still below 50) ---
    # Bump 2024-06-01 from 10 -> 40
    resp["clones"][0] = {"timestamp": "2024-06-01T00:00:00Z", "count": 40, "uniques": 9}
    mock_get.return_value.json.return_value = resp
    # Run 2: merge updated non-max; max annotation should remain the same
    fc.main()
    with open(fc.CLONES_FILE) as fh:
        data_after = json.load(fh)
    # The 'daily' list should still have exactly 3 entries (no duplication)
    assert len(data_after["daily"]) == 3
    max_anns_after = [a for a in data_after.get("annotations", []) if "daily max" in a["label"].lower()]
    assert len(max_anns_after) == 1, "There should still be exactly one max annotation"
    assert max_anns_after[0]["date"] == "2024-06-02", "Max annotation date must remain unchanged"
    assert max_anns_after[0]["label"] == "Daily max: 50", "Max annotation label must remain unchanged"
    # Sanity: totals should reflect the updated non-max day
    # Before: 10 + 50 + 12 = 72 ; After: 40 + 50 + 12 = 102
    assert data_after["total_clones"] == 102
