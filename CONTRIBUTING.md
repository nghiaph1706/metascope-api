# Contributing — MetaScope API

Thank you for wanting to contribute! Please read the guide below before getting started.

> **AI Agents**: also read `AGENTS.md` for the full code conventions and patterns.

---

## Workflow

```
1. Read AGENTS.md (required)
2. Setup hooks (run once):    make setup-hooks
3. Create branch from main:   git checkout -b feat/your-feature main
4. Code + test
5. Commit (hooks automatically run lint + format + validate commit message)
6. Push:                      git push -u origin feat/your-feature
7. Create PR on GitHub
```

---

## Branch Naming

Format: `<type>/<short-description>`

| Type | When to use | Example |
|---|---|---|
| `feat` | Adding a new feature | `feat/riot-client` |
| `fix` | Fixing a bug | `fix/rate-limit-429` |
| `refactor` | Refactoring without changing behavior | `refactor/service-layer` |
| `docs` | Documentation changes only | `docs/api-reference` |
| `test` | Adding/modifying tests only | `test/collector-coverage` |
| `chore` | Config, CI, deps, tooling | `chore/docker-compose` |

Rules:
- **kebab-case** (lowercase, hyphens)
- Keep it short, maximum 3–4 words after the type
- You may add a phase prefix: `feat/phase1-riot-client`
- Do not use names, dates, or ticket IDs

---

## Commit Messages

Format: [Conventional Commits](https://www.conventionalcommits.org/)

```
<type>(<scope>): <subject>

<body>           ← optional, explain WHY
<footer>         ← optional, breaking changes
```

### Type (required)

`feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

### Scope (optional)

The main module affected: `collector`, `api`, `models`, `services`, `core`, `docker`

### Subject (required)

- In English
- Do not capitalize the first letter
- No period at the end
- Imperative mood: "add", "fix", "update" — not "added", "fixes"
- Maximum 72 characters

### Examples

```bash
# ✅ Correct
feat(collector): add riot client with token bucket rate limiter
fix(api): return 404 instead of 500 when player not found
refactor(services): extract tier score calculation to pure function
test(collector): add unit tests for transformer edge cases
docs(api): add tier-list endpoint to API.md
chore(docker): upgrade python base image to 3.13

# ❌ Wrong
Added riot client                      # missing type, past tense
feat: update stuff                     # too vague
fix(api): Fixed the bug.               # past tense, period
FEAT(collector): Add Riot Client       # uppercase
```

### Body

Only write a body when the subject is not clear enough. Explain **why**, not **what**.

---

## Pull Requests

- PR title follows the commit format: `feat(collector): add riot client rate limiter`
- Write a brief what & why in the PR description
- All PRs must pass `make check && make test` before merging
- Do not merge if there are conflicts — rebase first

---

## Checklist before creating a PR

- [ ] Branch created from the latest `main`
- [ ] All tests pass: `make test`
- [ ] Lint + typecheck pass: `make check`
- [ ] Commit messages follow Conventional Commits format
- [ ] No committed `.env`, `__pycache__/`, `htmlcov/`, or generated files
- [ ] Updated `docs/API.md` if endpoints were added/modified

---

## Things NOT to do

- Do not commit directly to `main`
- Do not force push on a branch that is under review
- Do not commit sensitive files (`.env`, credentials, API keys)
- Do not commit generated files (`htmlcov/`, `__pycache__/`, `.mypy_cache/`)
- Do not write commit messages like `wip`, `fix fix fix`, `asdfgh`

---

## Dev Environment

Everything runs via Docker — see README.md for setup. All commands through `make`:

```bash
make dev          # Start full stack
make test         # Run tests (inside Docker)
make check        # Lint + typecheck (inside Docker)
make migrate      # Run DB migrations (inside Docker)
```

Do not run `pytest`, `ruff`, `alembic` directly on the host.

---

## Pre-commit Hooks

Hooks run automatically on every `git commit`. One-time setup:

```bash
make setup-hooks
```

### Hooks that run on commit (pre-commit stage)

| Hook | Description |
|---|---|
| `trailing-whitespace` | Remove trailing whitespace at end of lines |
| `end-of-file-fixer` | Ensure newline at end of file |
| `check-yaml` / `check-toml` | Validate YAML/TOML syntax |
| `check-added-large-files` | Block files > 500KB |
| `check-merge-conflict` | Block if conflict markers remain |
| `detect-private-key` | Block if committing a private key |
| `no-commit-to-branch` | **Block direct commits to `main`** |
| `ruff` | Lint + auto-fix |
| `ruff-format` | Auto-format code |
| `mypy` | Type checking |

### Hooks that run when writing a commit message (commit-msg stage)

| Hook | Description |
|---|---|
| `conventional-pre-commit` | **Validate commit message** follows Conventional Commits format |

If a hook fails → commit is rejected → fix the issue → commit again.

---

## Merge Rules

### Branch protection for `main`

| Rule | Details |
|---|---|
| **No direct push** | All changes go through PRs |
| **Require PR review** | At least 1 approval (if there are collaborators) |
| **Require status checks** | `make check` + `make test` must pass |
| **No force push** | `main` history must not be rewritten |
| **Delete branch after merge** | Auto-delete branch after merge |
| **Linear history** | Squash merge or rebase, no merge commits |

### Merge strategy

Use **squash merge** for all PRs:
- Combine all commits into 1 commit on `main`
- Commit message = PR title (already in Conventional Commits format)
- `main` history stays clean and easy to read

```bash
# GitHub will automatically squash when merging a PR
# Or manually:
git checkout main
git merge --squash feat/your-feature
git commit -m "feat(collector): add riot client with rate limiter"
```
