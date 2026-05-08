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

```
┌─────────────────────────────────────────────────────────┐
│                    Client / Consumer                     │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP / WebSocket
┌──────────────────────────▼──────────────────────────────┐
│              FastAPI Application (app/main.py)           │
│         Auth Middleware → Rate Limit → Router            │
└────────┬──────────────────────┬───────────────────────--┘
         │                      │
┌────────▼────────┐   ┌─────────▼────────┐
│  API Routes     │   │  Services Layer   │
│  app/api/       │   │  app/services/    │
└────────┬────────┘   └─────────┬────────┘
         │                      │
┌────────▼──────────────────────▼────────┐
│          Core Layer (app/core/)         │
│   DB Session │ Redis Client │ Config    │
└────────┬──────────────────────┬────────┘
         │                      │
┌────────▼────────┐   ┌─────────▼────────┐
│   PostgreSQL    │   │      Redis        │
│  + TimescaleDB  │   │  Cache + Broker   │
└─────────────────┘   └──────────────────┘

Background (Celery Workers):
┌──────────────────────────────────────┐
│  app/collector/  →  Data Ingestion   │
│  app/services/   →  Stats Compute    │
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
app/services/tier_list.py       → tests/unit/test_tier_list.py
app/collector/riot_client.py    → tests/unit/test_riot_client.py
app/api/routes/meta.py          → tests/integration/test_meta_routes.py
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

```
metascope/
├── AGENTS.md                   ← File này (đọc đầu tiên)
├── README.md                   ← Hướng dẫn setup và run
├── CHANGELOG.md                ← Log thay đổi theo version
│
├── docs/
│   ├── ARCHITECTURE.md         ← Kiến trúc chi tiết
│   ├── DATABASE.md             ← Schema, indexes, migrations
│   ├── API.md                  ← Endpoints reference
│   └── FEATURES.md             ← Danh sách tính năng và tiến độ
│
├── app/
│   ├── main.py                 ← FastAPI app, middleware, router mount
│   ├── core/
│   │   ├── config.py           ← Pydantic Settings (từ .env)
│   │   ├── database.py         ← Async engine, session factory
│   │   ├── redis.py            ← Redis client singleton
│   │   ├── exceptions.py       ← Custom exception classes
│   │   └── logging.py          ← Structured JSON logging setup
│   │
│   ├── models/
│   │   ├── base.py             ← Base model với created_at/updated_at
│   │   ├── user.py             ← User, OAuthAccount, Subscription, APIKey
│   │   ├── player.py           ← Player SQLAlchemy model
│   │   ├── match.py            ← Match, MatchParticipant, ParticipantUnit
│   │   ├── champion.py         ← Champion, Item, Augment, Trait
│   │   ├── comp.py             ← Composition, CompUnit
│   │   ├── stats.py            ← ChampionStats, ItemStats, AugmentStats, CompStats, TraitStats
│   │   ├── guide.py            ← Guide, GuideVote, GuideComment
│   │   ├── analysis.py         ← MatchAnalysis
│   │   ├── patch_notes.py      ← PatchNotes
│   │   └── localization.py     ← Localization
│   │
│   ├── schemas/
│   │   ├── auth.py             ← Login, Register, Token schemas
│   │   ├── player.py           ← Pydantic request/response schemas
│   │   ├── match.py
│   │   ├── meta.py             ← TierList, ChampionStats, CompStats response
│   │   ├── comp.py             ← Composition schemas
│   │   ├── guide.py            ← Guide CRUD schemas
│   │   ├── analysis.py         ← PostGame analysis schemas
│   │   ├── search.py           ← Search request/response
│   │   └── common.py           ← Pagination, ErrorResponse
│   │
│   ├── api/
│   │   ├── deps.py             ← FastAPI dependencies (DB session, auth)
│   │   └── routes/
│   │       ├── auth.py         ← /auth endpoints (register, login, oauth)
│   │       ├── admin.py        ← /admin endpoints (user mgmt)
│   │       ├── player.py       ← /player endpoints
│   │       ├── meta.py         ← /meta endpoints (tier list, stats, comps)
│   │       ├── guides.py       ← /guides endpoints (CRUD, votes, comments)
│   │       ├── patches.py      ← /patches endpoints (patch notes)
│   │       ├── game.py         ← /game endpoints (static data, rolling odds)
│   │       ├── search.py       ← /search endpoints
│   │       ├── leaderboard.py  ← /leaderboard endpoints
│   │       ├── matches.py      ← /matches endpoints
│   │       └── system.py       ← /health
│   │
│   ├── services/
│   │   ├── player_service.py   ← Business logic cho player
│   │   ├── auth_service.py     ← Auth, JWT, OAuth
│   │   ├── analysis_service.py ← Post-game analysis engine
│   │   ├── tier_list.py        ← Tier list algorithm
│   │   ├── comp_service.py     ← Comp detection + stats
│   │   ├── stats_service.py    ← Champion/item stats queries
│   │   ├── search_service.py   ← Fuzzy search logic
│   │   └── cache_service.py    ← Cache get/set helpers
│   │
│   └── collector/
│       ├── riot_client.py      ← HTTP client + rate limiter
│       ├── tft_collector.py    ← Orchestrate fetch → transform → store
│       ├── transformer.py      ← Parse Riot JSON → DB models
│       └── tasks.py            ← Celery tasks
│
├── tests/
│   ├── conftest.py             ← Fixtures: test DB, mock client, factory
│   ├── unit/
│   │   ├── test_riot_client.py
│   │   ├── test_transformer.py
│   │   ├── test_tier_list.py
│   │   ├── test_search_service.py
│   │   └── test_cache_service.py
│   └── integration/
│       ├── test_player_routes.py
│       ├── test_meta_routes.py
│       └── test_search_routes.py
│
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/               ← Migration files (auto-generated)
│
├── docker-compose.yml
├── docker-compose.test.yml     ← Dùng cho CI/CD
├── Dockerfile
├── .env.example
├── .env                        ← KHÔNG commit (có trong .gitignore)
├── pyproject.toml              ← Dependencies + tool config
├── alembic.ini
└── .gitignore
```

---

## 5. Patterns & Conventions

### 5.1 Service Layer Pattern

Route handlers chỉ làm 3 việc: validate input, gọi service, return response.
Business logic **luôn** nằm trong `app/services/`.

```python
# app/api/routes/meta.py
@router.get("/tier-list", response_model=TierListResponse)
async def get_tier_list(
    patch: str = Query(default="latest"),
    queue: str = Query(default="ranked"),
    db: AsyncSession = Depends(get_db),
) -> TierListResponse:
    """Trả tier list cho patch và queue type chỉ định."""
    return await tier_list_service.get_tier_list(db, patch=patch, queue=queue)

# app/services/tier_list.py  ← logic thực sự ở đây
async def get_tier_list(db: AsyncSession, patch: str, queue: str) -> TierListResponse:
    ...
```

### 5.2 Dependency Injection

```python
# app/api/deps.py — định nghĩa tất cả dependencies ở đây
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_current_api_key(
    api_key: str = Header(alias="X-API-Key", default=None)
) -> Optional[str]:
    ...
```

### 5.3 Cache Pattern

```python
# Mọi cache key theo format: tft:{resource}:{identifier}:{params}
# Ví dụ:
CACHE_KEYS = {
    "tier_list":      "tft:meta:tier:{patch}:{queue}",      # TTL 15 phút
    "comp_list":      "tft:meta:comps:{patch}:{queue}",     # TTL 15 phút
    "comp_detail":    "tft:comp:{id}:stats:{patch}",        # TTL 1 giờ
    "champion_stats": "tft:champion:{id}:stats:{patch}",    # TTL 1 giờ
    "search":         "tft:search:{query}:{type}",           # TTL 5 phút
    "player":         "tft:player:{puuid}",                  # TTL 30 phút
    "leaderboard":    "tft:leaderboard:{region}:{tier}",     # TTL 30 phút
}
```

### 5.4 Pagination

```python
# Tất cả list endpoints dùng cursor-based pagination
class PaginationParams:
    def __init__(self, limit: int = 20, cursor: Optional[str] = None):
        self.limit = min(limit, 100)  # max 100
        self.cursor = cursor

class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    next_cursor: Optional[str]
    total: Optional[int]
```

### 5.5 Response Format

```python
# Mọi error response theo format chuẩn
class ErrorResponse(BaseModel):
    error: str           # machine-readable code, ví dụ: "champion_not_found"
    message: str         # human-readable, ví dụ: "Champion 'Yas' not found"
    details: Optional[dict]  # thêm context nếu cần

# Success response tùy endpoint, nhưng luôn có:
# - data (chính)
# - meta (pagination, cache info nếu có)
```

---

## 6. Workflow khi nhận task

Khi nhận một task mới, **luôn** làm theo thứ tự:

```
1. ĐỌC file liên quan trong docs/ trước
2. KIỂM TRA xem đã có model/schema nào liên quan chưa
3. VIẾT schema Pydantic trước (defines the contract)
4. VIẾT SQLAlchemy model nếu cần bảng mới
5. VIẾT Alembic migration nếu có model mới
6. VIẾT service function (business logic)
7. VIẾT route handler (gọi service)
8. VIẾT tests (unit → integration)
9. CẬP NHẬT docs/API.md nếu thêm endpoint mới
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
    data = await httpx.get(f"https://asia.api.riotgames.com/...")  # SAI

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
