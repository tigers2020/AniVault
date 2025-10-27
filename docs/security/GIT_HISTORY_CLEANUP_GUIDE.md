# Git History Cleanup Guide

## Purpose
This guide provides instructions for scanning Git history for leaked secrets and cleaning them if found.

## Quick Scan

### Check for Secrets in Git History

```bash
# Scan all files in Git history
detect-secrets scan --all-files $(git ls-files)

# Or check specific patterns
git log --all --full-history --source -- '*config.toml' '*\.env'
```

### Check Current Tracked Files

```bash
# List all tracked files that should be ignored
git ls-files | Select-String -Pattern "config\.toml|\.env[^.]|secrets"
```

## If Secrets Are Found

### Option 1: Using BFG Repo-Cleaner (Recommended)

```bash
# 1. Create a fresh clone
git clone --mirror https://github.com/yourrepo/anivault.git anivault-cleanup

# 2. Download BFG
# https://rtyley.github.io/bfg-repo-cleaner/

# 3. Remove sensitive files from history
java -jar bfg.jar --delete-files config.toml anivault-cleanup.git
java -jar bfg.jar --delete-files '.env' anivault-cleanup.git

# 4. Clean up
cd anivault-cleanup.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 5. Force push (CAUTION: Coordinate with team!)
git push --force
```

### Option 2: Using git-filter-repo

```bash
# 1. Install git-filter-repo
pip install git-filter-repo

# 2. Remove sensitive files
git filter-repo --path config/config.toml --invert-paths
git filter-repo --path .env --invert-paths

# 3. Force push (CAUTION: Coordinate with team!)
git push --force
```

## After Cleanup

### 1. Revoke Exposed Secrets
- **TMDB API Key**: Regenerate at https://www.themoviedb.org/settings/api
- **Other Keys**: Revoke and regenerate all exposed credentials

### 2. Update Team
```markdown
⚠️ **SECURITY NOTICE**

Git history has been cleaned due to exposed secrets.
All team members must:

1. Delete local repo: `rm -rf anivault`
2. Re-clone: `git clone <url>`
3. Update API keys in `.env` file
4. Verify pre-commit hooks: `pre-commit install`
```

### 3. Verify Cleanup
```bash
# Scan again to confirm
detect-secrets scan --all-files $(git ls-files)

# Should show no secrets
```

## Prevention

### Pre-Commit Hook
Ensure `.pre-commit-config.yaml` has:
```yaml
- id: detect-secrets
  args: ['--baseline', '.secrets.baseline']
  stages: [commit, push]  # Both stages!
```

### Developer Checklist
- [ ] Never commit `config/config.toml` with real API keys
- [ ] Always use `.env` for secrets
- [ ] Use `.env.example` for documentation
- [ ] Run `detect-secrets scan` before pushing
- [ ] Check `git status` before committing

## Resources
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
- [git-filter-repo](https://github.com/newren/git-filter-repo)
- [detect-secrets](https://github.com/Yelp/detect-secrets)
- [GitHub: Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
