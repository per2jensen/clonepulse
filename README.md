# ClonePulse

**Your GitHub clone stats, visualized and celebrated.**  
Track weekly trends, highlight milestones, and share visual dashboards—all automatically.

[![Use this template](https://img.shields.io/badge/-Use%20this%20template-2ea44f?style=for-the-badge&logo=github)](https://github.com/per2jensen/clonepulse/generate)  
![Tests](https://github.com/per2jensen/clonepulse/actions/workflows/py-tests.yml/badge.svg)

---

## Add Badges to Your README

ClonePulse can generate badges you can embed in your repo:

[![# clones](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/per2jensen/clonepulse/main/clonepulse/badge_clones.json)](https://raw.githubusercontent.com/per2jensen/clonepulse/main/clonepulse/weekly_clones.png)  
[![Milestone](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/per2jensen/clonepulse/main/clonepulse/milestone_badge.json)](https://raw.githubusercontent.com/per2jensen/clonepulse/main/clonepulse/weekly_clones.png)

---

## Example dashboards

### Weekly dashboard (default)
A weekly clone activity chart is automatically updated and saved in `clonepulse/weekly_clones.png`.

- Runs every Monday morning
- Discards partial weeks
- Shows only complete Monday–Sunday periods

![Standard clone dashboard, last 16 weeks](example/default.png)
<sub>Command: `python src/clonepulse/generate_clone_dashboard.py --user per2jensen --repo clonepulse`</sub>


### Reproducible window (`--start` + `--weeks`)
![Dashboard starting 2025-08-15 for 6 weeks](example/start-example.png)  
<sub>Command: `python src/clonepulse/generate_clone_dashboard.py --start 2025-09-01 --weeks 8  --user per2jensen --repo clonepulse`</sub>

### Calendar year (`--year`)
![Dashboard for calendar year 2025 (to date)](example/year-example.png)  
<sub>Command: `python src/clonepulse/generate_clone_dashboard.py --year 2025 --user per2jensen --repo clonepulse`</sub>

---

## Quick Setup

1. **Create a GitHub Token**  
   See [🔐 Token Setup](#-token-setup) below.

2. **Drop essentials into your repo**  
   Copy the contents of `clonepulse/` and `src/clonepulse/` plus the workflows in `.github/workflows/`.

3. **Add badges to your README**  
   Replace `your-username/your-repo`:

   ```markdown
   [![# clones](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/your-username/your-repo/main/clonepulse/badge_clones.json)](https://github.com/your-username/your-repo/blob/main/clonepulse/weekly_clones.png)

   [![Milestone](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/your-username/your-repo/main/clonepulse/milestone_badge.json)](https://github.com/your-username/your-repo/blob/main/clonepulse/weekly_clones.png)
   ```

4. **Configure the workflow**  
   Update `fetch_clones.yml` with your `--user` and `--repo`.

   ```yaml
   - name: Run fetch_clones.py
     env:
       TOKEN: ${{ secrets.CLONEPULSE_METRICS }}
     run: |
       PYTHONPATH=src python src/clonepulse/fetch_clones.py \
         --user <your GitHub login> \
         --repo <your repo>
   ```

5. **Generate the dashboard in your workflow**  

   Default (last 12 weeks):

   ```yaml
   - name: Render dashboard
     run: PYTHONPATH=src python src/clonepulse/generate_clone_dashboard.py
   ```

   Reproducible window:

   ```yaml
   - name: Render dashboard
     run: |
       PYTHONPATH=src python src/clonepulse/generate_clone_dashboard.py \
         --start 2025-06-02 --weeks 8
   ```

   **Dashboard title & repo label**  
   - Banner title always says “Weekly Clone Metrics”.  
   - If you provide `--user` and `--repo`, the banner also shows `user/repo`.
   - If only one is provided, that single value is shown.  
   - If neither flag is passed, the script falls back to env vars `GITHUB_USER` / `GITHUB_REPO` for the label.

   **Additional CLI options** (can also be used locally):

   ```bash
   PYTHONPATH=src python src/clonepulse/generate_clone_dashboard.py \
     [--user your-username] \
     [--repo your-repo] \
     [--start YYYY-MM-DD --weeks N] \
     [--year YYYY]
   ```

---

## Token Setup

ClonePulse fetches traffic stats from the GitHub API. This requires a Personal Access Token (PAT).

### Permissions

For **public repos**:
- Administration: Read-only
- Metadata: Read-only

For **private repos**:
- Administration: Read-only
- Metadata: Read-only
- Contents: Read-only
- Traffic: Read-only

### How to Create the Token

1. Visit [https://github.com/settings/tokens](https://github.com/settings/tokens)  
   Click **Generate new token → Fine-grained token**

2. Configure:
   - Name: e.g. `your-repo_ClonePulse`
   - Expiration: e.g. 90 days
   - Resource owner: Your user or organization
   - Repository access: select your repo
   - Permissions: set as above

3. Generate and copy the token. (You only see it once.)

### Add Token to Secrets

1. Go to your GitHub repository:  
   **Settings → Secrets and variables → Actions → New repository secret**

2. Name the secret:  
   `CLONEPULSE_METRICS`

3. Paste the token and save.

### Use in Workflow

```yaml
- name: Run fetch_clones.py
  env:
    TOKEN: ${{ secrets.CLONEPULSE_METRICS }}
  run: python src/clonepulse/fetch_clones.py
```

---

## Contributing

Found a bug or want to suggest a feature?  
[Open an issue](https://github.com/per2jensen/clonepulse/issues) or send a PR.

---

## License

ClonePulse is licensed under [MIT](LICENSE).
