# MetaScope API 🎮

TFT (Teamfight Tactics) meta analytics backend — tier list, champion stats, player lookup, and fuzzy search.

Hệ thống backend phân tích meta TFT — tier list, champion stats, tra cứu player, và tìm kiếm thông minh.

[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-red)](https://redis.io)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

---

## Features / Tính năng

- **Player Lookup** — look up players by Riot ID, view match history and stats / tra cứu player theo Riot ID
- **Tier List** — auto-updated S/A/B/C/D tier per patch / tự động cập nhật theo patch
- **Compositions** — top comps, trending comps, best augments/items per comp
- **Champion Stats** — win rate, top 4 rate, avg placement, best items
- **Fuzzy Search** — typo-tolerant search (`yas` → `Yasuo`) / tìm kiếm chịu lỗi chính tả
- **Leaderboard** — top players by region and rank tier / xếp hạng theo region
- **Player Analysis** — most played comps, strengths/weaknesses / phân tích điểm mạnh/yếu
- **Trait Stats** — win rate, avg placement per trait and tier level
- **Item Cheat Sheet** — crafting table, best holders per item / bảng craft items
- **Rolling Odds** — shop odds per level / tỷ lệ shop theo level
- **Guides** — user-generated comp guides, upvote/downvote, comments
- **Patch Notes** — summarized patch notes, auto-detect buffs/nerfs from data / tóm tắt patch notes
- **Post-Game Analysis** — "What went wrong?" match analysis with improvement suggestions / phân tích trận thua
- **Vietnamese-First** — all insights/analysis bilingual Vietnamese-English / song ngữ Việt-Anh
- **Multi-region** — collect data from multiple regions (VN2, KR, EUW, NA...)
- **Background Jobs** — Celery workers for automatic data collection and computation

---

## Requirements / Yêu cầu

| Tool | Version | Install |
|---|---|---|
| Python | 3.13+ | [python.org](https://python.org) |
| Docker | 24+ | [docker.com](https://docker.com) |
| Docker Compose | 2.20+ | Bundled with Docker Desktop |
| Make | any | `brew install make` / `apt install make` |

---

## Quick Start / Bắt đầu nhanh (5 min)

### 1. Clone & setup

```bash
git clone https://github.com/nghiaph1706/metascope-api.git
cd metascope-api

# Copy env file
cp .env.example .env
```

### 2. Add Riot API Key / Thêm Riot API Key

Get your key at [developer.riotgames.com](https://developer.riotgames.com), then edit `.env`:

```env
RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### 3. Start / Khởi chạy

```bash
# Start the full stack (DB + Redis + API + Worker)
make dev

# Wait ~30s for DB to start, then run migrations
make migrate

# Seed champion/item data from DataDragon (requires internet)
make seed
```

### 4. Verify / Kiểm tra

```bash
# Health check
curl http://localhost:8000/health

# Swagger UI
open http://localhost:8000/docs

# Try player lookup (replace with real name)
curl "http://localhost:8000/api/v1/player/vn2/PlayerName/VN2"
```

---

## Project Structure / Cấu trúc project

Domain-driven architecture — each feature is a self-contained package.

```
metascope-api/
├── app/
│   ├── main.py             ← FastAPI entry point
│   ├── core/               ← Shared: config, DB, Redis, base classes
│   ├── auth/               ← Authentication & users
│   ├── player/             ← Player lookup & profile
│   ├── match/              ← Match data & history
│   ├── meta/               ← Champions, items, tier list, stats
│   ├── composition/        ← Comp detection & ranking
│   ├── analysis/           ← Post-game "What went wrong?"
│   ├── guide/              ← User-generated guides
│   ├── search/             ← Fuzzy search
│   ├── leaderboard/        ← Rankings
│   ├── patch_notes/        ← Patch notes
│   ├── game/               ← Static game data
│   └── ports/              ← External APIs (Riot, DataDragon)
├── tests/                  ← Mirrors source structure
├── alembic/                ← Database migrations
├── docs/                   ← Architecture, API, Database docs
└── .env.example
```

---

## Common Commands / Lệnh thường dùng

```bash
# ── Development (all run inside Docker) ──────────────
make dev            # Start full stack (API + DB + Redis + Workers)
make worker         # Start Celery worker
make shell          # Python shell inside container

# ── Database ─────────────────────────────────────────
make migrate        # Run latest migrations
make migration msg="add champion table"  # Create new migration
make db-reset       # Drop + recreate DB (dev only)
make seed           # Seed champion/item data from DataDragon

# ── Testing ──────────────────────────────────────────
make test           # Run all tests
make test-unit      # Unit tests only
make test-int       # Integration tests only
make test-cov       # Tests + coverage report

# ── Code Quality ─────────────────────────────────────
make lint           # ruff check
make format         # ruff format
make typecheck      # mypy

# ── Docker ───────────────────────────────────────────
make up             # docker compose up -d
make down           # docker compose down
make logs           # docker compose logs -f
make restart        # down + up
```

---

## Environment Variables / Biến môi trường

Create `.env` from `.env.example`. Required variables:

| Variable | Required | Description |
|---|---|---|
| `RIOT_API_KEY` | ✅ | Get at developer.riotgames.com |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `REDIS_URL` | ✅ | Redis connection string |
| `SECRET_KEY` | ✅ | Random string for JWT auth |
| `ENVIRONMENT` | — | `development` / `production` (default: development) |
| `LOG_LEVEL` | — | `DEBUG` / `INFO` / `WARNING` (default: INFO) |
| `DEFAULT_REGION` | — | Riot platform (default: vn2) |
| `RATE_LIMIT_PER_SECOND` | — | Riot API rate limit (default: 20) |
| `CACHE_TTL_TIER_LIST` | — | Seconds, default: 900 (15 min) |
| `CACHE_TTL_CHAMPION_STATS` | — | Seconds, default: 3600 (1 hour) |

---

## API Overview

Base URL: `http://localhost:8000/api/v1`

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/player/{region}/{game_name}/{tag_line}` | Lookup player |
| GET | `/player/{puuid}/matches` | Match history |
| GET | `/player/{puuid}/analysis` | Player analysis |
| GET | `/meta/tier-list` | Tier list by patch |
| GET | `/meta/comps` | Top compositions by patch |
| GET | `/meta/comps/{id}` | Composition details |
| GET | `/meta/comps/trending` | Rising/falling comps |
| GET | `/meta/champions/{id}/stats` | Champion stats |
| GET | `/meta/compare` | Compare 2 patches |
| GET | `/meta/traits` | Trait/synergy stats |
| GET | `/meta/items/cheatsheet` | Item crafting table |
| GET | `/game/rolling-odds` | Shop odds per level |
| GET | `/guides` | User-generated guides |
| GET | `/patches/{patch}/notes` | Summarized patch notes |
| GET | `/search` | Fuzzy search |
| GET | `/leaderboard` | Top players |
| WS | `/ws/live/{puuid}` | Live match tracking |

Full reference: `docs/API.md` or `/docs` (Swagger UI).

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.115, Uvicorn |
| Database | PostgreSQL 16 + TimescaleDB |
| Cache / Broker | Redis 7 |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Task Queue | Celery 5 |
| HTTP Client | httpx (async) |
| Validation | Pydantic v2 |
| Testing | pytest, pytest-asyncio, httpx |
| Linting | ruff, mypy |
| Container | Docker, docker-compose |

---

## Development Guidelines

See `AGENTS.md` for full conventions. Summary:

- **Async/await** for all I/O
- **Type hints** on every function
- **Docstrings** Google style on all public functions
- **Test file** for every module
- **No hardcoded** config — use `settings.*`

---

## Features

See `docs/FEATURES.md` for full list and progress.

---

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for full rules. Summary:

1. Read `AGENTS.md` first
2. Create branch from `main`: `git checkout -b feat/your-feature`
3. Run `make test` and `make check` before committing
4. Use Conventional Commits: `feat(scope): subject`
5. PR title follows commit message format

---

## License

MIT License — see [LICENSE](LICENSE).
