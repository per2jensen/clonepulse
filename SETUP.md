# 🛠️ After Creating Your Repo from This Template

1. **Set up your secrets:**
   - Go to **Settings → Secrets and variables → Actions**
   - Add a secret named `CLONEPULSE_METRICS` with your GitHub PAT

2. **Edit `.github/workflows/fetch_clones.yml`:**
   - Add your GitHub username and repo to the arguments (if not passed as env vars)

3. **Enable GitHub Actions:**
   - Make sure workflows are enabled and cron triggers are active

4. **Customize badge URLs:**
   - Replace `<your-user>/<your-repo>` in badge URLs with your repo details

5. **Remove `.github/workflows/py-tests.yml`:**
   - Unless you hack on this, it can be removed

6. **Remove `example/`:**
   - This can be removed, used in README.md
