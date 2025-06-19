# After Creating Your Repo from This Template, do a bit of cleanup

1. **Create a GitHub token:**

2. **Use your secret:**
   - Add a secret to you repo. The token is the value.

3. **Edit `.github/workflows/fetch_clones.yml`:**
   - Add your GitHub username and repo to the arguments (if not passed as env vars).

4. **Enable GitHub Actions:**
   - Make sure workflows are enabled and cron triggers are active.

5. **Customize badge URLs:**
   - Replace `<your-user>/<your-repo>` in badge URLs with your repo details.

6. **Remove `.github/workflows/py-tests.yml`:**
   - Unless you hack on this, it can be removed.

7. **Remove `example/`:**
   - This can be removed, used in README.md.

---

The [README.md](https://github.com/per2jensen/clonepulse/blob/main/README.md) contains instructions on how to move the functionality to your own repository.
