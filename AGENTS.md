# AGENTS.md — MetaScope API

This is the main guide for all AI coding agents (OpenCode, Claude Code, Cursor, Copilot).
Read this file **first** before working on any task.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Mandatory Coding Rules](#3-mandatory-coding-rules)
4. [Directory Structure](#4-directory-structure)
5. [Patterns & Conventions](#5-patterns--conventions)
6. [Workflow When Receiving a Task](#6-workflow-when-receiving-a-task)
7. [Git Conventions](#7-git-conventions)
8. [Things You Must NOT Do](#8-things-you-must-not-do)
9. [Reference Documentation](#9-reference-documentation)

---

## 1. Project Overview

**MetaScope API** is a backend system for TFT (Teamfight Tactics) meta analysis.

| Property | Value |
|---|---|
| Language | Python 3.13 |
| Framework | FastAPI + Uvicorn |
| Database | PostgreSQL 16 + TimescaleDB |
| Cache | Redis 7 |
| Task Queue | Celery + Redis broker |
| ORM | SQLAlchemy 2.0 (async) |
| Migration | Alembic |
| Testing | pytest + pytest-asyncio |
| Container | Docker + docker-compose |

**Further reading:**
- `docs/ARCHITECTURE.md` — detailed architecture and data flow
- `docs/DATABASE.md` — schema, indexes, queries
- `docs/API.md` — endpoints, request/response format
- `docs/FEATURES.md` — feature list and progress

---

## 2. System Architecture

Domain-driven architecture — each feature is self-contained with its own router, service, models, and schemas.

```
┌─────────────────────────────────────────────────────────┐
│                    Client / Consumer                     │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP / WebSocket
┌──────────────────────────▼──────────────────────────────┐
│              FastAPI Application (app/main.py)           │
│         Middleware → Mount domain routers                │
└────────┬──────────────────────┬────────────────────────-┘
         │                      │
┌────────▼──────────────────────▼────────────────────────┐
│           Domain Modules (app/{domain}/)                │
│  router.py → service.py → models.py + schemas.py       │
│  Each domain: self-contained, no cross-domain imports   │
└────────┬──────────────────────┬────────────────────────┘
         │                      │
┌────────▼────────┐   ┌─────────▼────────┐
│  Core Layer     │   │  Ports Layer     │
│  app/core/      │   │  app/ports/      │
│  DB, Redis,     │   │  Riot API,       │
│  Config, Auth   │   │  DataDragon      │
└────────┬────────┘   └─────────┬────────┘
         │                      │
┌────────▼────────┐   ┌─────────▼────────┐
│   PostgreSQL    │   │   Riot Games     │
│  + TimescaleDB  │   │   External API   │
├─────────────────┤   └──────────────────┘
│     Redis       │
│  Cache + Broker │
└─────────────────┘

Background (Celery Workers):
┌──────────────────────────────────────┐
│  app/{domain}/jobs.py per domain     │
│  autodiscovered by app/core/celery   │
└──────────────────────────────────────┘
```

---

## 3. Mandatory Coding Rules

### 3.1 Async/Await — EVERYWHERE

```python
# ✅ CORRECT — always use async
async def get_champion_stats(champion_id: str, patch: str) -> ChampionStats:
    async with get_session() as session:
        result = await session.execute(...)
        return result.scalars().first()

# ❌ WRONG — do not use sync in async context
def get_champion_stats(champion_id: str, patch: str) -> ChampionStats:
    session = Session()  # blocking
    return session.query(...).first()
```

### 3.2 Type Hints — COMPLETE everywhere

```python
# ✅ CORRECT
from typing import Optional
from uuid import UUID

async def get_player(
    puuid: str,
    region: str = "asia",
    include_stats: bool = False,
) -> Optional[PlayerResponse]:
    ...

# ❌ WRONG — missing type hints
async def get_player(puuid, region="asia"):
    ...
```

### 3.3 Docstring — EVERY public function/class/method

```python
# ✅ CORRECT — Google style docstring
async def calculate_tier_score(
    win_rate: float,
    avg_placement: float,
    pick_rate: float,
) -> float:
    """Calculate the tier score for a champion.

    Formula: win_rate * 0.35 + placement_score * 0.35 + pick_rate * 0.30
    Placement score = (8 - avg_placement) / 7, normalized to [0, 1].

    Args:
        win_rate: Win rate (1st place), value 0.0–1.0.
        avg_placement: Average placement, value 1.0–8.0.
        pick_rate: Pick rate (games_played / total_games), value 0.0–1.0.

    Returns:
        Tier score from 0.0 to 1.0. Higher = better.

    Raises:
        ValueError: If avg_placement is not within the range [1, 8].
    """
    if not 1.0 <= avg_placement <= 8.0:
        raise ValueError(f"avg_placement must be 1–8, got: {avg_placement}")
    placement_score = (8.0 - avg_placement) / 7.0
    return win_rate * 0.35 + placement_score * 0.35 + pick_rate * 0.30
```

### 3.4 Pytest — EACH module has a corresponding test file

```
app/player/service.py          → tests/player/test_service.py
app/player/router.py           → tests/player/test_router.py
app/meta/service.py            → tests/meta/test_service.py
app/ports/riot/client.py       → tests/ports/test_riot_client.py
```

Each test file must have at least:
- Test happy path
- Test edge case (empty data, min sample size)
- Test error case (API down, invalid input)

### 3.5 Error Handling

```python
# ✅ CORRECT — custom exceptions, do not raise generic Exception
from app.core.exceptions import RiotAPIError, ChampionNotFoundError

async def fetch_match(match_id: str) -> dict:
    try:
        response = await self._client.get(f"/tft/match/v1/matches/{match_id}")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise RiotAPIError("Rate limit exceeded", retry_after=int(e.response.headers.get("Retry-After", 1)))
        if e.response.status_code == 404:
            raise MatchNotFoundError(f"Match {match_id} not found")
        raise RiotAPIError(f"Riot API error: {e.response.status_code}")
```

### 3.6 Config — only from `app/core/config.py`

```python
# ✅ CORRECT
from app.core.config import settings
api_key = settings.riot_api_key

# ❌ WRONG — do not use os.environ directly in business logic
import os
api_key = os.environ["RIOT_API_KEY"]
```

### 3.7 Docker-first — ALL commands run inside Docker

The entire dev environment runs via Docker Compose. **Do not** run directly on the host.

```bash
# ✅ CORRECT — run via Docker
make test               # docker compose exec api pytest
make lint               # docker compose exec api ruff check
make migrate            # docker compose exec api alembic upgrade head
docker compose exec api python -m app.scripts.seed_champions

# ❌ WRONG — do not run directly on the host
pytest
ruff check app/
alembic upgrade head
python -m app.scripts.seed_champions
```

Reason: ensures Python version (3.13), dependencies, and environment variables are always consistent across all developers and CI.

---

## 4. Directory Structure

Organized by **domain-driven** approach — each feature is a fully self-contained package.

References:
- [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices)
- [Auth0 FastAPI Best Practices](https://auth0.com/blog/fastapi-best-practices/)

```
metascope-api/
├── AGENTS.md                   ← This file (read first)
├── README.md
├── CONTRIBUTING.md
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATABASE.md
│   ├── API.md
│   └── FEATURES.md
│
├── app/
│   ├── main.py                 ← FastAPI app entry point, mount routers
│   │
│   ├── core/                   ← Shared infrastructure (no business logic)
│   │   ├── config.py           ← Pydantic Settings (from .env)
│   │   ├── database.py         ← Async engine, session factory, get_db
│   │   ├── redis.py            ← Redis client, get_redis
│   │   ├── celery.py           ← Celery app instance, autodiscover
│   │   ├── logging.py          ← Structured JSON logging (structlog)
│   │   ├── models.py           ← Base, UUIDMixin, TimestampMixin
│   │   ├── schemas.py          ← CustomBaseModel, PaginatedResponse, ErrorResponse
│   │   ├── dependencies.py     ← Shared deps: get_db, get_redis, get_current_user
│   │   └── exceptions.py       ← MetaScopeError base + shared exceptions
│   │
│   ├── auth/                   ← Authentication & user management
│   │   ├── router.py           ← /auth endpoints
│   │   ├── schemas.py          ← Login, Register, Token DTOs
│   │   ├── models.py           ← User, OAuthAccount, Subscription, APIKey
│   │   ├── service.py          ← JWT, OAuth, password hashing
│   │   ├── dependencies.py     ← get_current_user, require_premium, require_admin
│   │   ├── constants.py
│   │   └── exceptions.py       ← UnauthorizedError, ForbiddenError...
│   │
│   ├── player/                 ← Player lookup & profile
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py           ← Player
│   │   ├── service.py
│   │   ├── jobs.py             ← sync_player_profiles
│   │   ├── dependencies.py
│   │   └── exceptions.py
│   │
│   ├── match/                  ← Match data & history
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py           ← Match, MatchParticipant, ParticipantUnit
│   │   ├── service.py
│   │   └── exceptions.py
│   │
│   ├── meta/                   ← Champions, items, augments, traits, tier list
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py           ← Champion, Item, Augment, Trait, ChampionStats...
│   │   ├── service.py          ← tier_score, calculate_stats
│   │   ├── jobs.py             ← calculate_champion_stats, calculate_item_stats
│   │   ├── constants.py
│   │   └── exceptions.py
│   │
│   ├── composition/            ← Comp detection & ranking
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py           ← Composition, CompUnit, CompStats
│   │   ├── service.py          ← detect_comps, comp_stats
│   │   ├── jobs.py             ← detect_and_calculate_comps
│   │   └── exceptions.py
│   │
│   ├── analysis/               ← Post-game "What went wrong?"
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py           ← MatchAnalysis
│   │   ├── service.py          ← analyze_match, generate_insights
│   │   ├── jobs.py             ← analyze_recent_matches
│   │   └── constants.py        ← Issue types, severity levels
│   │
│   ├── guide/                  ← User-generated guides
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py           ← Guide, GuideVote, GuideComment
│   │   ├── service.py
│   │   └── exceptions.py
│   │
│   ├── search/                 ← Fuzzy search
│   │   ├── router.py
│   │   ├── schemas.py
│   │   └── service.py
│   │
│   ├── leaderboard/            ← Rankings
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py           ← LeaderboardEntry
│   │   ├── service.py
│   │   └── jobs.py             ← update_leaderboard
│   │
│   ├── patch_notes/            ← Patch notes & meta changes
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py           ← PatchNotes
│   │   ├── service.py
│   │   └── jobs.py             ← auto_detect_patch_changes
│   │
│   ├── game/                   ← Static game data (rolling odds, cheatsheet)
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py           ← RollingOdds, Localization
│   │   └── service.py
│   │
│   └── ports/                  ← External service adapters
│       ├── riot/
│       │   ├── client.py       ← RiotClient (HTTP + rate limiter)
│       │   ├── transformer.py  ← Parse Riot JSON → domain models
│       │   └── rate_limiter.py ← Token bucket
│       └── data_dragon/
│           └── client.py       ← Static data fetcher (champions, items)
│
├── tests/                      ← Mirror source structure
│   ├── conftest.py             ← Shared fixtures
│   ├── player/
│   │   ├── test_service.py
│   │   └── test_router.py
│   ├── match/
│   ├── meta/
│   ├── auth/
│   └── ports/
│       └── test_riot_client.py
│
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── pyproject.toml
├── alembic.ini
├── .pre-commit-config.yaml
└── .gitignore
```

### Organization Rules

1. **Each domain package contains everything it needs**: `router.py`, `schemas.py`, `models.py`, `service.py`, and optionally `jobs.py`, `dependencies.py`, `constants.py`, `exceptions.py`
2. **No cross-domain imports** — if something needs to be shared, put it in `core/`
3. **`core/`** contains only infrastructure, no business logic
4. **`ports/`** contains adapters for external services (Riot API, DataDragon)
5. **Tests mirror source** — `tests/player/test_service.py` tests `app/player/service.py`

---

## 5. Patterns & Conventions

### 5.1 Domain Module Pattern

Each domain module follows the same structure:

```python
# app/meta/router.py — HTTP interface
@router.get("/tier-list", response_model=TierListResponse)
async def get_tier_list(
    patch: str = Query(default="latest"),
    queue: str = Query(default="ranked"),
    db: AsyncSession = Depends(get_db),
) -> TierListResponse:
    """Return the tier list for the specified patch and queue type."""
    return await service.get_tier_list(db, patch=patch, queue=queue)

# app/meta/service.py — business logic
async def get_tier_list(db: AsyncSession, patch: str, queue: str) -> TierListResponse:
    ...

# app/meta/models.py — SQLAlchemy models
class ChampionStats(UUIDMixin, Base):
    __tablename__ = "champion_stats"
    ...

# app/meta/schemas.py — Pydantic DTOs (request + response + validation)
class TierListResponse(CustomBaseModel):
    patch: str
    tiers: dict[str, list[ChampionTierEntry]]

# app/meta/jobs.py — Celery tasks
@celery_app.task
def calculate_champion_stats(patch: str) -> None:
    ...
```

### 5.2 Dependency Injection

```python
# app/core/dependencies.py — shared deps
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# app/auth/dependencies.py — feature-specific deps
async def get_current_user(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login")),
    db: AsyncSession = Depends(get_db),
) -> User:
    ...

async def require_premium(user: User = Depends(get_current_user)) -> User:
    if user.tier != "premium":
        raise PremiumRequiredError()
    return user
```

### 5.3 Cache Pattern

```python
# Cache keys defined in module constants or core
CACHE_KEYS = {
    "tier_list":      "tft:meta:tier:{patch}:{queue}",
    "comp_list":      "tft:meta:comps:{patch}:{queue}",
    "comp_detail":    "tft:comp:{id}:stats:{patch}",
    "champion_stats": "tft:champion:{id}:stats:{patch}",
    "search":         "tft:search:{query}:{type}",
    "player":         "tft:player:{puuid}",
    "leaderboard":    "tft:leaderboard:{region}:{tier}",
}
```

### 5.4 Pagination

```python
# app/core/schemas.py
class PaginationParams:
    def __init__(self, limit: int = 20, cursor: Optional[str] = None):
        self.limit = min(limit, 100)
        self.cursor = cursor

class PaginatedResponse(CustomBaseModel, Generic[T]):
    data: list[T]
    next_cursor: Optional[str]
    total: Optional[int]
```

### 5.5 Response Format

```python
# Error response — consistent across all endpoints
class ErrorResponse(CustomBaseModel):
    error: str           # machine-readable: "champion_not_found"
    message: str         # human-readable: "Champion 'Yas' not found"
    details: Optional[dict]

# Document exceptions in OpenAPI
@router.get(
    "/champions/{id}/stats",
    responses={404: {"model": ErrorResponse, "description": "Champion not found"}},
)
```

### 5.6 Custom Base Model

```python
# app/core/schemas.py
class CustomBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
```

---

## 6. Workflow When Receiving a Task

When receiving a new task, **always** follow this order:

```
1. READ relevant files in docs/ first
2. IDENTIFY which domain is affected (app/player/, app/meta/,...)
3. WRITE schemas.py first (defines the contract)
4. WRITE models.py if a new table is needed
5. WRITE Alembic migration if there is a new model
6. WRITE service.py (business logic)
7. WRITE router.py (call service, inject deps)
8. WRITE jobs.py if there is a background task
9. WRITE tests (tests/{domain}/test_service.py, test_router.py)
10. UPDATE docs/API.md if a new endpoint is added
```

### Checklist before completing a task

- [ ] All new functions have complete type hints
- [ ] All new functions have docstrings (Google style)
- [ ] All I/O is async
- [ ] There is a corresponding test file with at least 3 test cases
- [ ] No hardcoded config (use `settings.*`)
- [ ] No `print()` — use `logger.info/warning/error`
- [ ] `pytest` passes before marking as done
- [ ] `ruff check .` has no errors

### Commit rules (IMPORTANT)

**NEVER commit without verifying first.** Mandatory process:

```
1. Code complete → build succeeds (docker compose build)
2. Container runs (docker compose up)
3. Tests pass (make test)
4. Endpoint returns correct data (curl verify)
5. ONLY THEN commit
```

**Do NOT fix errors one at a time.** Before fixing, trace the full impact:

```
Example: changing Python version →
  ✅ CORRECT: check all deps compatibility, Dockerfile build deps,
           migration driver — fix EVERYTHING at once, verify once
  ❌ WRONG:  fix asyncpg → commit → psycopg2 error → commit → gcc error → commit
```

If fixing one thing causes another issue → STOP, think through the entire chain, fix everything, then verify.

### Updating progress

After completing a feature, **always** update `docs/FEATURES.md`:
- Mark `[x]` for completed features
- New sessions read this file to know the current status, no need to re-explore source

---

## 7. Git Conventions

> Full details: see **[CONTRIBUTING.md](CONTRIBUTING.md)**

Summary:

- **Branch**: `<type>/<short-description>` — kebab-case, e.g. `feat/riot-client`, `fix/rate-limit-429`
- **Commit**: Conventional Commits — `feat(collector): add riot client with rate limiter`
- **Subject**: English, imperative mood, no capitalization, no period, max 72 characters
- **PR title**: same format as commit message
- Always run `make check && make test` before creating a PR
- Do not commit directly to `main`, do not force push, do not commit `.env`

---

## 8. Things You Must NOT Do

```python
# ❌ Do not use sync DB in async code
session.query(Champion).filter(...)

# ❌ Do not hardcode config values
headers = {"X-Riot-Token": "RGAPI-abc123"}

# ❌ Do not catch Exception too broadly without logging
try:
    ...
except Exception:
    pass

# ❌ Do not call Riot API directly from route handler
@router.get("/player/{puuid}")
async def get_player(puuid: str):
    data = await httpx.get(f"https://asia.api.riotgames.com/...")  # WRONG — use ports/riot/client.py

# ❌ Do not import across domains
from app.player.service import get_player  # WRONG if inside app/meta/
# If sharing is needed → put it in app/core/

# ❌ Do not put business logic in migrations
# Migrations should only contain: CREATE/ALTER/DROP table, CREATE INDEX

# ❌ Do not commit directly to main if tests fail
# Always run pytest first

# ❌ Do not use * imports
from app.models import *  # WRONG
```

---

## 9. Reference Documentation

| Document | Link |
|---|---|
| Riot TFT API | https://developer.riotgames.com/apis#tft-match-v1 |
| FastAPI docs | https://fastapi.tiangolo.com |
| SQLAlchemy 2.0 async | https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html |
| Alembic | https://alembic.sqlalchemy.org |
| Celery | https://docs.celeryq.dev |
| TimescaleDB | https://docs.timescale.com |
| pg_trgm | https://www.postgresql.org/docs/current/pgtrgm.html |
| Pydantic v2 | https://docs.pydantic.dev/latest |
| pytest-asyncio | https://pytest-asyncio.readthedocs.io |
