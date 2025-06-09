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
    assert "500 clones" in milestone["message"]


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
