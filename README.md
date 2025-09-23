# ClonePulse

**Your GitHub clone stats, visualized and celebrated.**  
Track weekly trends, highlight milestones, and share visual dashboards—all automatically.

[![Use this template](https://img.shields.io/badge/-Use%20this%20template-2ea44f?style=for-the-badge&logo=github)](https://github.com/per2jensen/clonepulse/generate)

![Tests](https://github.com/per2jensen/clonepulse/actions/workflows/py-tests.yml/badge.svg)

---

## 🏷️ Add Badges to Your README

These are live examples of the badges.

[![# clones](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/per2jensen/clonepulse/main/clonepulse/badge_clones.json)](https://raw.githubusercontent.com/per2jensen/clonepulse/main/clonepulse/weekly_clones.png)
[![Milestone](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/per2jensen/clonepulse/main/clonepulse/milestone_badge.json)](https://raw.githubusercontent.com/per2jensen/clonepulse/main/clonepulse/weekly_clones.png)

The Milestone badge automatically starts celebrating #clones milestones:

- [See the celebration badge in action here](https://github.com/per2jensen/dar-backup)
- Checkout [the script](https://github.com/per2jensen/clonepulse/blob/main/src/clonepulse/fetch_clones.py) to see milestones and configuration of the badge.
- You can adjust milestones in `fetch_clones.py` → `MILESTONES` list.

---

## What is ClonePulse?

`ClonePulse` is a GitHub-friendly toolchain that fetches, tracks, and visualizes repository clone activity.

It offers:

- **Daily clone tracking** (total + unique)
- **12-week visual dashboard** (.PNG image)
- **Automatic milestone detection** (e.g., 500, 1K, 2K+ clones)
- **Auto-annotations** for clone spikes  
  Annotations can be manually added to `clonepulse/fetch_clones.json` (for example the date of a post on reddit)
- **Badge generation** for README inclusion
- **GitHub Actions** support for automation

---

## 📷 Example dashboard

> A weekly clone activity chart is automatically updated and saved in `clonepulse/weekly_clones.png`.

It is intended to run every Monday morning. Data from the current week is discarded. Only full Monday–Sunday weeks are shown.

![Clone Dashboard Example](example/weekly_clones.png)

---

## 🧰 Dashboard generator CLI

`src/clonepulse/generate_clone_dashboard.py` supports reproducible windows and safer input validation.

### Options

- `--start YYYY-MM-DD`  
  Start **reporting date** (typically a Monday). Window is inclusive.  
  Only annotations within the plotted window are drawn.  

  **Validation:** 
  - if the date is in the future the script prints  
  `ERROR: --start date is in the future: <date>` and exits with code `2`.

- `--weeks N`  
  Number of weeks to display starting at `--start` (default: 12).

  This option is ignored if --year is provided.

  **Validation:** 
  - if `N` is negative the script prints  
  `ERROR: --weeks must be non-negative. Got <N>.` and exits with code `2`.

- `--year YYYY`
  Selects a **calendar year** to plot. All weeks starting in that year are aggregated
  and displayed.  
  Mutually exclusive with `--start` and `--weeks`.  

  **Validation:**  
  - If the year is in the future, the script prints  
    `ERROR: --year is in the future: <year>` and exits with code `2`.  
  - If there is no data for that year, an empty dashboard is generated.

### Behavior

- Weekly aggregation: Monday–Sunday, reported on the following Monday.
- Current (partial) week excluded.
- Duplicate-date annotations are **stacked vertically** to avoid overlap.
- Long labels are truncated on **word boundaries** to a safe length.

### Examples

```bash
# Default: last 12 weeks
python src/clonepulse/generate_clone_dashboard.py

# Reproducible window: 8 weeks from 2025-06-02
python src/clonepulse/generate_clone_dashboard.py --start 2025-06-02 --weeks 8

# Full year 2025
python src/clonepulse/generate_clone_dashboard.py --year 2025
````

---

## Setup instructions

1. Create a token, and add it to your repo (see below)

2. [Drop the essentials](#how-to-drop-the-essentials-into-another-repository) into your repo

3. Copy these badge links to your README.md and replace `your-username/your-repo` with your actual GitHub username and repository name:

```text
[![# clones](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/your-username/your-repo/main/clonepulse/badge_clones.json)](https://github.com/your-username/your-repo/blob/main/clonepulse/weekly_clones.png)

[![Milestone](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/your-username/your-repo/main/clonepulse/milestone_badge.json)](https://github.com/your-username/your-repo/blob/main/clonepulse/weekly_clones.png)
```

4. Modify `.github/workflows/fetch_clones.yml`

Modify the values given to `--user` and `--repo` in the workflow task shown below:

```yaml
      - name: Run fetch_clones.py
        env:
          TOKEN: ${{ secrets.CLONEPULSE_METRICS }}
        run: |
          PYTHONPATH=src python src/clonepulse/fetch_clones.py \
            --user per2jensen \
            --repo clonepulse
```

to

```yaml
      - name: Run fetch_clones.py
        env:
          TOKEN: ${{ secrets.CLONEPULSE_METRICS }}
        run: |
          PYTHONPATH=src python src/clonepulse/fetch_clones.py \
            --user <your Github login> \
            --repo <your repo to fetch clone stats from>
```

5. Generate the dashboard PNG in your workflow

Default (last 12 weeks):

```yaml
      - name: Render dashboard (default window)
        run: |
          PYTHONPATH=src python src/clonepulse/generate_clone_dashboard.py
```

Reproducible window:

```yaml
      - name: Render dashboard (reproducible window)
        run: |
          PYTHONPATH=src python src/clonepulse/generate_clone_dashboard.py \
            --start 2025-06-02 --weeks 8
```

---

## 🔐 Create GitHub Token for ClonePulse

ClonePulse fetches traffic (clone) stats from the GitHub API. This requires a Personal Access Token (PAT) with read-only access to `Read access to administration and metadata`. Here's how to create one securely and use it with GitHub Actions.

### Token Requirements

For public repositories, a fine-grained token with `Read access to administration and metadata` access is sufficient.

For private repositories, you will also need:

* Repository contents: Read-only
* Repository metadata: Read-only
* Repository traffic: Read-only

### How to Create a Fine-Grained Token

Visit: [https://github.com/settings/tokens](https://github.com/settings/tokens)

Click "Generate new token" → "Fine-grained token"

Configure:

Name: e.g., `"your repository"_ClonePulse`
Expiration: e.g., 90 days
Resource owner: Your user or organization
Repository access: Select the **specific repo**

Set the following permissions on the token:

* "Administration": Read-only
* "Metadata":  Read-only
* For Private repos you might need more

Click "Generate token" and copy the value of the token to secure storage immediately. You only see it once.

## Use the token in your repository

After having created the secret, you must now put it into the repository where you want to use it.

1. Go to your GitHub repository:
   **Settings → Secrets and variables → Actions → New repository secret**

2. Name the secret:
   `CLONEPULSE_METRICS`

3. Paste the token you copied and save.

The workflow references the secret as an environment variable in this way:

```yaml
- name: Run fetch_clones.py
  env:
    TOKEN: ${{ secrets.CLONEPULSE_METRICS }}
  run: python src/clonepulse/fetch_clones.py
```

---

## How to drop the essentials into another repository

Create a tarball with the needed artifacts as shown below and extract the contents into your repository of choice.

Your destination repository must be somewhere on disk in a local git repo.

Take a look at `SETUP.md` also.

```bash
# create tarball with
#  - 2 .github workflows
#  - artifacts in clonepulse/
#  - the python scripts in src/clonepulse/
tar --exclude='.github/workflows/py-tests.yml' \
    --exclude='clonepulse/weekly_clones.png' \
    --exclude='*/__pycache__' --exclude='*.pyc' \
    -cvf clonepulse-artifacts.tar \
    {src/clonepulse,clonepulse,.github/workflows}

# extract artifacts to destination repo
	ar -xvf clonepulse-artifacts.tar -C <your repo>
```

After extraction, ensure that:

* `clonepulse/` and `src/clonepulse/` exist in your repo root
* GitHub Actions are in `.github/workflows/`

---

## Installation (dev setup)

These instructions are only needed if you want to hack on ClonePulse

```bash
# python3 and a few packages are needed.
# This works on Ubuntu 24.04
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip

git clone https://github.com/your-user/clonepulse.git
cd clonepulse
./build.sh  # Creates virtualenv and installs dependencies
```

This sets up a Python virtual environment and installs dependencies listed in `pyproject.toml`.

---

## Contributing

Found a bug or have a suggestion
Feel free to [open an issue](https://github.com/per2jensen/clonepulse/issues) or submit a pull request
