# MetaScope API — Quick Rules

This is a short reference. **Full guide: see [AGENTS.md](AGENTS.md)** (read it first for complete context).

## Critical Rules

### Git — NEVER do this
- ❌ **Do not commit directly to `main`**
- ❌ Do not force push to branches under review
- ❌ Do not commit `.env`, credentials, or private keys

### Workflow
- ✅ Always create a branch: `git checkout -b feat/your-feature main`
- ✅ All changes go through PR → code review → merge
- ✅ Run `make check && make test` before creating PR

## Architecture
- Language: Python 3.13, async/await everywhere
- Framework: FastAPI + SQLAlchemy 2.0 (async)
- Dev: Docker-first — all commands through `make`

## Pre-commit Hooks (must install)
```bash
pip install pre-commit
pre-commit install --install-hooks
```
Hooks block direct commits to `main`, run lint/typecheck on every commit.

## API Integration (3rd party)
- ✅ Before implementing: run `curl` to see actual sample response
- ✅ Note rate limits (requests/minute, requests/sec) before designing integration
- ✅ Cache responses when possible to avoid hitting rate limits

## Testing Requirements
- ✅ Every router needs `tests/{domain}/test_router.py`
- ✅ Every job (Celery task) needs `tests/{domain}/test_jobs.py`
- ✅ Job is only "done" when verified working — run manually, check output/logs

## Full Documentation
See `AGENTS.md` for:
- Directory structure
- Coding patterns & conventions
- Step-by-step workflow
- Complete list of do's and don'ts

## Quick Start
```bash
make dev          # Start services
make test         # Run tests
make check        # Lint + typecheck
```
