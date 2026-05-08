# AGENTS.md — MetaScope API

Đây là file hướng dẫn chính cho tất cả AI coding agents (OpenCode, Claude Code, Cursor, Copilot).
Đọc file này **trước tiên** trước khi làm bất kỳ task nào.

---

## Mục lục

1. [Tổng quan dự án](#1-tổng-quan-dự-án)
2. [Kiến trúc hệ thống](#2-kiến-trúc-hệ-thống)
3. [Quy tắc code bắt buộc](#3-quy-tắc-code-bắt-buộc)
4. [Cấu trúc thư mục](#4-cấu-trúc-thư-mục)
5. [Patterns & Conventions](#5-patterns--conventions)
6. [Workflow khi nhận task](#6-workflow-khi-nhận-task)
7. [Git Conventions](#7-git-conventions)
8. [Những điều KHÔNG được làm](#8-những-điều-không-được-làm)
9. [Tài liệu tham chiếu](#9-tài-liệu-tham-chiếu)

---

## 1. Tổng quan dự án

**MetaScope API** là một hệ thống backend phân tích meta TFT (Teamfight Tactics).

| Thuộc tính | Giá trị |
|---|---|
| Ngôn ngữ | Python 3.13 |
| Framework | FastAPI + Uvicorn |
| Database | PostgreSQL 16 + TimescaleDB |
| Cache | Redis 7 |
| Task Queue | Celery + Redis broker |
| ORM | SQLAlchemy 2.0 (async) |
| Migration | Alembic |
| Testing | pytest + pytest-asyncio |
| Container | Docker + docker-compose |

**Đọc thêm:**
- `docs/ARCHITECTURE.md` — chi tiết kiến trúc và data flow
- `docs/DATABASE.md` — schema, indexes, queries
- `docs/API.md` — endpoints, request/response format
- `docs/FEATURES.md` — danh sách tính năng và tiến độ

---

## 2. Kiến trúc hệ thống

Domain-driven architecture — mỗi feature tự chứa router, service, models, schemas.

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

## 3. Quy tắc code bắt buộc

### 3.1 Async/Await — TOÀN BỘ

```python
# ✅ ĐÚNG — luôn dùng async
async def get_champion_stats(champion_id: str, patch: str) -> ChampionStats:
    async with get_session() as session:
        result = await session.execute(...)
        return result.scalars().first()

# ❌ SAI — không dùng sync trong async context
def get_champion_stats(champion_id: str, patch: str) -> ChampionStats:
    session = Session()  # blocking
    return session.query(...).first()
```

### 3.2 Type Hints — ĐẦY ĐỦ mọi nơi

```python
# ✅ ĐÚNG
from typing import Optional
from uuid import UUID

async def get_player(
    puuid: str,
    region: str = "asia",
    include_stats: bool = False,
) -> Optional[PlayerResponse]:
    ...

# ❌ SAI — thiếu type hint
async def get_player(puuid, region="asia"):
    ...
```

### 3.3 Docstring — MỌI function/class/method public

```python
# ✅ ĐÚNG — Google style docstring
async def calculate_tier_score(
    win_rate: float,
    avg_placement: float,
    pick_rate: float,
) -> float:
    """Tính điểm tier cho một champion.

    Công thức: win_rate * 0.35 + placement_score * 0.35 + pick_rate * 0.30
    Placement score = (8 - avg_placement) / 7, normalize về [0, 1].

    Args:
        win_rate: Tỷ lệ thắng (1st place), giá trị 0.0–1.0.
        avg_placement: Vị trí trung bình, giá trị 1.0–8.0.
        pick_rate: Tỷ lệ pick (games_played / total_games), giá trị 0.0–1.0.

    Returns:
        Điểm tier từ 0.0 đến 1.0. Cao hơn = tốt hơn.

    Raises:
        ValueError: Nếu avg_placement không nằm trong khoảng [1, 8].
    """
    if not 1.0 <= avg_placement <= 8.0:
        raise ValueError(f"avg_placement phải từ 1–8, nhận: {avg_placement}")
    placement_score = (8.0 - avg_placement) / 7.0
    return win_rate * 0.35 + placement_score * 0.35 + pick_rate * 0.30
```

### 3.4 Pytest — MỖI module có file test tương ứng

```
app/player/service.py          → tests/player/test_service.py
app/player/router.py           → tests/player/test_router.py
app/meta/service.py            → tests/meta/test_service.py
app/ports/riot/client.py       → tests/ports/test_riot_client.py
```

Mỗi test file phải có ít nhất:
- Test happy path
- Test edge case (empty data, min sample size)
- Test error case (API down, invalid input)

### 3.5 Error Handling

```python
# ✅ ĐÚNG — custom exceptions, không raise generic Exception
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

### 3.6 Config — chỉ từ `app/core/config.py`

```python
# ✅ ĐÚNG
from app.core.config import settings
api_key = settings.riot_api_key

# ❌ SAI — không dùng os.environ trực tiếp trong business logic
import os
api_key = os.environ["RIOT_API_KEY"]
```

### 3.7 Docker-first — MỌI command chạy trong Docker

Toàn bộ môi trường dev chạy qua Docker Compose. **Không** chạy trực tiếp trên host.

```bash
# ✅ ĐÚNG — chạy qua Docker
make test               # docker compose exec api pytest
make lint               # docker compose exec api ruff check
make migrate            # docker compose exec api alembic upgrade head
docker compose exec api python -m app.scripts.seed_champions

# ❌ SAI — không chạy trực tiếp trên host
pytest
ruff check app/
alembic upgrade head
python -m app.scripts.seed_champions
```

Lý do: đảm bảo Python version (3.13), dependencies, và environment variables luôn đồng nhất giữa mọi developer và CI.

---

## 4. Cấu trúc thư mục

Tổ chức theo **domain-driven** — mỗi feature là một package tự chứa đầy đủ.

Tham khảo:
- [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices)
- [Auth0 FastAPI Best Practices](https://auth0.com/blog/fastapi-best-practices/)

```
metascope-api/
├── AGENTS.md                   ← File này (đọc đầu tiên)
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
│   ├── core/                   ← Shared infrastructure (không chứa business logic)
│   │   ├── config.py           ← Pydantic Settings (từ .env)
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

### Quy tắc tổ chức

1. **Mỗi domain package chứa đủ**: `router.py`, `schemas.py`, `models.py`, `service.py`, và optional `jobs.py`, `dependencies.py`, `constants.py`, `exceptions.py`
2. **Không import chéo giữa domains** — nếu cần share, đặt vào `core/`
3. **`core/`** chỉ chứa infrastructure, không business logic
4. **`ports/`** chứa adapters cho external services (Riot API, DataDragon)
5. **Tests mirror source** — `tests/player/test_service.py` test `app/player/service.py`

---

## 5. Patterns & Conventions

### 5.1 Domain Module Pattern

Mỗi domain module có cấu trúc giống nhau:

```python
# app/meta/router.py — HTTP interface
@router.get("/tier-list", response_model=TierListResponse)
async def get_tier_list(
    patch: str = Query(default="latest"),
    queue: str = Query(default="ranked"),
    db: AsyncSession = Depends(get_db),
) -> TierListResponse:
    """Trả tier list cho patch và queue type chỉ định."""
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
# Cache keys định nghĩa trong module constants hoặc core
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

## 6. Workflow khi nhận task

Khi nhận một task mới, **luôn** làm theo thứ tự:

```
1. ĐỌC file liên quan trong docs/ trước
2. XÁC ĐỊNH domain nào bị ảnh hưởng (app/player/, app/meta/,...)
3. VIẾT schemas.py trước (defines the contract)
4. VIẾT models.py nếu cần bảng mới
5. VIẾT Alembic migration nếu có model mới
6. VIẾT service.py (business logic)
7. VIẾT router.py (gọi service, inject deps)
8. VIẾT jobs.py nếu có background task
9. VIẾT tests (tests/{domain}/test_service.py, test_router.py)
10. CẬP NHẬT docs/API.md nếu thêm endpoint mới
```

### Checklist trước khi hoàn thành task

- [ ] Tất cả function mới có type hints đầy đủ
- [ ] Tất cả function mới có docstring (Google style)
- [ ] Tất cả I/O là async
- [ ] Có test file tương ứng với ít nhất 3 test cases
- [ ] Không có hardcoded config (dùng `settings.*`)
- [ ] Không có `print()` — dùng `logger.info/warning/error`
- [ ] Chạy `pytest` pass trước khi done
- [ ] Chạy `ruff check .` không có error

### Quy tắc commit (QUAN TRỌNG)

**KHÔNG BAO GIỜ commit mà chưa verify.** Quy trình bắt buộc:

```
1. Code xong → build thành công (docker compose build)
2. Container chạy được (docker compose up)
3. Tests pass (make test)
4. Endpoint trả đúng data (curl verify)
5. SAU ĐÓ mới commit
```

**KHÔNG fix từng lỗi một.** Trước khi fix, trace toàn bộ impact:

```
Ví dụ: đổi Python version →
  ✅ ĐÚNG: check tất cả deps compatibility, Dockerfile build deps,
           migration driver — fix HẾT cùng lúc, verify 1 lần
  ❌ SAI:  fix asyncpg → commit → lỗi psycopg2 → commit → lỗi gcc → commit
```

Nếu fix 1 thứ mà lòi thứ khác → DỪNG LẠI, suy nghĩ toàn bộ chain, fix hết rồi mới verify.

### Cập nhật tiến độ

Sau khi hoàn thành feature, **luôn** cập nhật `docs/FEATURES.md`:
- Đánh `[x]` cho feature đã xong
- Session mới đọc file này để biết trạng thái hiện tại, không cần explore lại source

---

## 7. Git Conventions

> Chi tiết đầy đủ: xem **[CONTRIBUTING.md](CONTRIBUTING.md)**

Tóm tắt:

- **Branch**: `<type>/<short-description>` — kebab-case, ví dụ `feat/riot-client`, `fix/rate-limit-429`
- **Commit**: Conventional Commits — `feat(collector): add riot client with rate limiter`
- **Subject**: tiếng Anh, imperative mood, không viết hoa, không dấu chấm, tối đa 72 ký tự
- **PR title**: cùng format commit message
- Luôn chạy `make check && make test` trước khi tạo PR
- Không commit trực tiếp vào `main`, không force push, không commit `.env`

---

## 8. Những điều KHÔNG được làm

```python
# ❌ Không dùng sync DB trong async code
session.query(Champion).filter(...)

# ❌ Không hardcode giá trị config
headers = {"X-Riot-Token": "RGAPI-abc123"}

# ❌ Không bắt Exception quá rộng mà không log
try:
    ...
except Exception:
    pass

# ❌ Không gọi Riot API trực tiếp từ route handler
@router.get("/player/{puuid}")
async def get_player(puuid: str):
    data = await httpx.get(f"https://asia.api.riotgames.com/...")  # SAI — dùng ports/riot/client.py

# ❌ Không import chéo giữa domains
from app.player.service import get_player  # SAI nếu đang trong app/meta/
# Nếu cần share → đặt vào app/core/

# ❌ Không để migration chứa business logic
# Migration chỉ được chứa: CREATE/ALTER/DROP table, CREATE INDEX

# ❌ Không commit trực tiếp vào main nếu test fail
# Luôn chạy pytest trước

# ❌ Không dùng * import
from app.models import *  # SAI
```

---

## 9. Tài liệu tham chiếu

| Tài liệu | Link |
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
