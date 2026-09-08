# GitHub Repository Setup

Use a **private repository** if the project will contain internal table names,
schemas, business logic, or documentation. The sample project contains no
credentials or real query results, but internal replacements may be sensitive.

## Option A: GitHub CLI

From the `bifrost-sql-template-tool` directory:

```bash
git init
git branch -M main
git add .
git status
git commit -m "Initial commit: add SQL template tool"
```

Authenticate if required:

```bash
gh auth login
gh auth status
```

Create a new private repository and push `main`:

```bash
gh repo create bifrost-sql-template-tool \
  --private \
  --source=. \
  --remote=origin \
  --push
```

Verify it:

```bash
git remote -v
git status
gh repo view --web
```

To create a public repository instead, first confirm that the SQL, documentation,
and history contain no internal identifiers or confidential information. Then
replace `--private` with `--public`.

## Option B: GitHub website and Git

1. Sign in to GitHub and select **New repository**.
2. Enter `bifrost-sql-template-tool` as the repository name.
3. Select **Private** for internal work.
4. Do not initialize it with a README, `.gitignore`, or license; those files are
   already included locally.
5. Select **Create repository**.
6. Copy the HTTPS URL shown by GitHub.
7. Run the following commands, replacing the placeholder URL:

```bash
git init
git branch -M main
git add .
git status
git commit -m "Initial commit: add SQL template tool"
git remote add origin https://github.com/YOUR-USERNAME/bifrost-sql-template-tool.git
git push -u origin main
```

If Git requests authentication, use the browser/device sign-in flow or an
approved credential helper. Do not place a personal access token in the remote
URL, a script, or a committed file.

## Recommended repository controls

After the first push:

1. Protect the `main` branch.
2. Require a pull request and at least one review.
3. Require passing tests before merge.
4. Enable secret scanning and dependency alerts where available.
5. Add a `CODEOWNERS` rule for the data-platform reviewer.
6. Prohibit committed query outputs and secrets.

Before each push, inspect exactly what will be committed:

```bash
git status
git diff --cached
```
