# MetaScope API 🎮

Hệ thống backend phân tích meta TFT (Teamfight Tactics) — tier list, champion stats, player lookup, và fuzzy search.

[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-red)](https://redis.io)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

---

## Tính năng

- **Player Lookup** — tra cứu player theo Riot ID, xem match history và stats
- **Tier List** — S/A/B/C/D tier tự động cập nhật theo từng patch
- **Compositions** — top comps, trending comps, best augments/items per comp
- **Champion Stats** — win rate, top 4 rate, avg placement, best items
- **Fuzzy Search** — tìm tướng/trang bị với typo tolerance (`yas` → `Yasuo`)
- **Leaderboard** — top players theo region và rank tier
- **Player Analysis** — phân tích comp hay dùng, điểm mạnh/yếu
- **Trait Stats** — win rate, avg placement theo trait và tier level
- **Item Cheat Sheet** — bảng craft items, best holders per item
- **Rolling Odds** — tỷ lệ shop theo level
- **Guides** — user-generated comp guides, upvote/downvote, comments
- **Patch Notes** — tóm tắt patch notes, auto-detect buffs/nerfs từ data
- **Post-Game Analysis** — "What went wrong?" phân tích trận thua, gợi ý cải thiện
- **Vietnamese-First** — toàn bộ insights/analysis song ngữ Việt-Anh
- **Multi-region** — collect data từ nhiều region (VN2, KR, EUW, NA...)
- **Background Jobs** — Celery workers tự động thu thập và tính toán data

---

## Yêu cầu

| Tool | Version | Cài đặt |
|---|---|---|
| Python | 3.13+ | [python.org](https://python.org) |
| Docker | 24+ | [docker.com](https://docker.com) |
| Docker Compose | 2.20+ | Bundled với Docker Desktop |
| Make | bất kỳ | `brew install make` / `apt install make` |

---

## Bắt đầu nhanh (5 phút)

### 1. Clone và setup

```bash
git clone https://github.com/yourusername/metascope-api.git
cd metascope-api

# Copy file env
cp .env.example .env
```

### 2. Điền Riot API Key

Lấy key tại [developer.riotgames.com](https://developer.riotgames.com), sau đó mở `.env`:

```env
RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### 3. Khởi chạy

```bash
# Khởi chạy toàn bộ stack (DB + Redis + API + Worker)
docker compose up -d

# Chờ ~30 giây để DB khởi động, sau đó chạy migrations
make migrate

# Seed dữ liệu champion/item từ DataDragon (cần internet)
make seed
```

### 4. Kiểm tra

```bash
# Health check
curl http://localhost:8000/health

# Swagger UI
open http://localhost:8000/docs

# Thử lookup player (thay bằng tên thật)
curl "http://localhost:8000/api/v1/player/PlayerName/VN2"
```

---

## Cấu trúc project

Domain-driven architecture — mỗi feature tự chứa đầy đủ.

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
├── tests/                  ← Mirror source structure
├── alembic/                ← Database migrations
├── docs/                   ← Architecture, API, Database docs
└── .env.example
```

---

## Lệnh thường dùng

```bash
# ── Development (tất cả chạy trong Docker) ──────────
make dev            # Start full stack (API + DB + Redis + Workers)
make worker         # Start Celery worker
make shell          # Python shell trong container

# ── Database ─────────────────────────────────────────
make migrate        # Chạy migrations mới nhất
make migration msg="add champion table"  # Tạo migration mới
make db-reset       # Xóa và tạo lại DB (dev only)
make seed           # Seed champion/item data từ DataDragon

# ── Testing ──────────────────────────────────────────
make test           # Chạy tất cả tests
make test-unit      # Chỉ unit tests
make test-int       # Chỉ integration tests
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

## Biến môi trường

Tạo file `.env` từ `.env.example`. Các biến bắt buộc:

| Biến | Bắt buộc | Mô tả |
|---|---|---|
| `RIOT_API_KEY` | ✅ | Lấy tại developer.riotgames.com |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `REDIS_URL` | ✅ | Redis connection string |
| `SECRET_KEY` | ✅ | Random string cho JWT (nếu dùng auth) |
| `ENVIRONMENT` | — | `development` / `production` (default: development) |
| `LOG_LEVEL` | — | `DEBUG` / `INFO` / `WARNING` (default: INFO) |
| `DEFAULT_REGION` | — | Riot platform (default: vn2) |
| `RATE_LIMIT_PER_SECOND` | — | Riot API rate limit (default: 20) |
| `CACHE_TTL_TIER_LIST` | — | Giây, default: 900 (15 phút) |
| `CACHE_TTL_CHAMPION_STATS` | — | Giây, default: 3600 (1 giờ) |

---

## API Overview

Base URL: `http://localhost:8000/api/v1`

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/player/{name}/{tag}` | Lookup player |
| GET | `/player/{puuid}/matches` | Match history |
| GET | `/player/{puuid}/analysis` | Player analysis |
| GET | `/meta/tier-list` | Tier list theo patch |
| GET | `/meta/comps` | Top compositions theo patch |
| GET | `/meta/comps/{id}` | Chi tiết composition |
| GET | `/meta/comps/trending` | Comps đang tăng/giảm |
| GET | `/meta/champions/{id}/stats` | Stats một champion |
| GET | `/meta/compare` | So sánh 2 patch |
| GET | `/meta/traits` | Trait/synergy stats |
| GET | `/meta/items/cheatsheet` | Bảng craft items |
| GET | `/game/rolling-odds` | Tỷ lệ shop theo level |
| GET | `/guides` | User-generated guides |
| GET | `/patches/{patch}/notes` | Patch notes tóm tắt |
| GET | `/search` | Fuzzy search |
| GET | `/leaderboard` | Top players |
| WS | `/ws/live/{puuid}` | Live match tracking |

Xem đầy đủ tại `docs/API.md` hoặc `/docs` (Swagger UI).

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

Xem `AGENTS.md` để biết đầy đủ convention. Tóm tắt:

- **Async/await** cho mọi I/O
- **Type hints** đầy đủ mọi function
- **Docstring** Google style cho mọi function public
- **Test file** tương ứng mọi module
- **Không hardcode** config — dùng `settings.*`

---

## Features

Xem đầy đủ tại `docs/FEATURES.md`.

---

## Contributing

Xem **[CONTRIBUTING.md](CONTRIBUTING.md)** để biết đầy đủ quy tắc. Tóm tắt:

1. Đọc `AGENTS.md` trước
2. Tạo branch từ `main`: `git checkout -b feat/your-feature`
3. Chạy `make test` và `make check` trước khi commit
4. Commit theo Conventional Commits: `feat(scope): subject`
5. PR title cùng format commit message

---

## License

MIT License — xem [LICENSE](LICENSE).
