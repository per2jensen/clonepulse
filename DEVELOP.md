# ClonePulse Developer Guide

This document is for contributors and developers working on ClonePulse itself.

---

## Dashboard generator CLI

`src/clonepulse/generate_clone_dashboard.py` supports reproducible windows and input validation.

### Options

- `--start YYYY-MM-DD`  
  Start reporting date (Monday). Window is inclusive.  
  Validation:  
  - Future dates → error and exit code `2`.

- `--weeks N`  
  Number of weeks to display from `--start` (default: 12).  
  Ignored if `--year` is provided.  
  Validation:  
  - Negative values → error and exit code `2`.

- `--year YYYY`  
  Select a calendar year to plot. All weeks starting in that year are included.  
  Mutually exclusive with `--start` and `--weeks`.  
  Validation:  
  - Future years → error and exit code `2`.  
  - No data → empty dashboard generated.

### Behavior

- Weekly aggregation: Monday–Sunday, reported the following Monday.  
- Current (partial) week excluded.  
- Duplicate-date annotations are stacked vertically.  
- Long labels truncated on word boundaries.

### Examples

```bash
# Default: last 12 weeks
python src/clonepulse/generate_clone_dashboard.py

# Reproducible window: 8 weeks from 2025-06-02
python src/clonepulse/generate_clone_dashboard.py --start 2025-06-02 --weeks 8

# Full year 2025
python src/clonepulse/generate_clone_dashboard.py --year 2025
```

---

## How to drop ClonePulse into another repo

Bundle essentials into a tarball:

```bash
tar --exclude='.github/workflows/py-tests.yml' \
    --exclude='clonepulse/weekly_clones.png' \
    --exclude='*/__pycache__' --exclude='*.pyc' \
    -cvf clonepulse-artifacts.tar \
    {src/clonepulse,clonepulse,.github/workflows}

tar -xvf clonepulse-artifacts.tar -C <target-repo>
```

Ensure:
- `clonepulse/` and `src/clonepulse/` exist at repo root
- Workflows are in `.github/workflows/`

---

## Installation (dev setup)

To hack on ClonePulse locally:

```bash
# Ubuntu 24.04 example
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip

git clone https://github.com/your-user/clonepulse.git
cd clonepulse
./build.sh
```

This sets up a virtual environment and installs dependencies from `pyproject.toml`.

---

## Contributing

- Use Black, flake8, and isort for formatting.  
- Add or update tests for all code changes.  
- Ensure CI passes before PR.  
- Confirm contributions are MIT licensed.

---

## Testing

Run tests with:

```bash
pytest -v
```

CI runs these automatically.
