# Features — MetaScope API

Danh sách tính năng, theo thứ tự ưu tiên. Check `[x]` khi hoàn thành.

---

## Core Infrastructure

- [x] Docker Compose stack chạy được (API + Postgres + Redis + Celery)
- [x] Core layer: `database.py`, `redis.py`, `logging.py`
- [x] Alembic setup + initial migration (enable pg_trgm, TimescaleDB)
- [x] SQLAlchemy models: Player, Match, Champion, Item, Augment
- [ ] Seed script: champions + items từ DataDragon
- [ ] Multi-region data collection (VN2, KR, EUW, NA...)

## Data Collection

- [x] Riot API client (`riot_client.py`)
  - Token bucket rate limiter (20 req/s, 100 req/2min)
  - asyncio.Semaphore cho concurrent limit
  - Retry với exponential backoff khi 429
- [x] Transformer: parse Riot JSON → DB models
- [ ] TFT Collector: fetch → deduplicate → batch insert
- [ ] Sync player profiles (periodic job, resolve puuid → player info)
- [ ] Celery worker + beat scheduler
- [ ] Collect data từ multiple regions (configurable region list)

## Player

- [x] `GET /player/{region}/{game_name}/{tag_line}` — lookup player
- [ ] `GET /player/{puuid}/matches` — match history (cursor pagination)
- [ ] `GET /player/{puuid}/stats` — tổng hợp stats
- [ ] `GET /player/{puuid}/analysis` — comp hay dùng, điểm mạnh/yếu

## Meta & Analytics

- [ ] Stats calculation service (champion, item, augment stats)
- [ ] Tier list algorithm (`win_rate*0.35 + placement*0.35 + pick_rate*0.30`)
- [ ] `GET /meta/tier-list` — tier list theo patch
- [ ] `GET /meta/champions/{id}/stats` — stats chi tiết champion
- [ ] `GET /meta/items/{id}/stats` — item stats
- [ ] `GET /meta/augments/{id}/stats` — augment stats
- [ ] `GET /meta/compare` — so sánh 2 patch
- [ ] `GET /meta/patches` — danh sách patches có data

## Compositions

- [ ] Comp detection algorithm (trait-based fingerprinting từ match data)
- [ ] Comp stats calculation (win rate, top4, placement, pick rate per comp)
- [ ] Best augments/items per comp (per-stage breakdown)
- [ ] `GET /meta/comps` — top comps theo patch, xếp tier
- [ ] `GET /meta/comps/{id}` — chi tiết comp: units, items, augments, history
- [ ] `GET /meta/comps/trending` — comps đang tăng/giảm mạnh nhất
- [ ] Celery task `detect_and_calculate_comps` (mỗi 2 giờ)

## Traits / Synergies

- [ ] `GET /meta/traits` — danh sách traits với stats (win rate, avg placement per active tier)
- [ ] `GET /meta/traits/{id}/stats` — stats chi tiết trait (per tier level, per patch)
- [ ] Trait combo analysis: trait X + trait Y cùng nhau hiệu quả không

## Items

- [ ] `GET /meta/items/cheatsheet` — bảng craft: component A + B = item X
- [ ] `GET /meta/items/{id}/best-holders` — top champions dùng item này hiệu quả nhất
- [ ] Item recommendation per champion + per comp

## Game Data (Static)

- [ ] `GET /game/rolling-odds` — tỷ lệ shop theo level (seed từ Riot static data)
- [ ] `GET /game/champions` — danh sách champions với base stats
- [ ] `GET /game/items` — danh sách items với recipes
- [ ] `GET /game/augments` — danh sách augments theo tier
- [ ] `GET /game/traits` — danh sách traits với breakpoints
- [ ] Auto-update khi có patch mới (Celery task check DataDragon)

## Guides (User-Generated Content)

- [ ] User registration + authentication (email/password hoặc OAuth)
- [ ] `POST /guides` — tạo guide mới (comp guide, how-to-play)
- [ ] `GET /guides` — list guides (sort by votes, recency, patch)
- [ ] `GET /guides/{id}` — đọc guide chi tiết
- [ ] `PUT /guides/{id}` — edit guide (chỉ author)
- [ ] `DELETE /guides/{id}` — xóa guide (author hoặc admin)
- [ ] `POST /guides/{id}/vote` — upvote/downvote
- [ ] `POST /guides/{id}/comments` — comment trên guide
- [ ] `GET /guides/{id}/comments` — list comments (threaded)
- [ ] Link guide tới composition (optional)
- [ ] Markdown support cho guide content
- [ ] Filter guides theo patch, comp, author

## Patch Notes

- [ ] `GET /patches` — danh sách patches
- [ ] `GET /patches/{patch}/notes` — patch notes tóm tắt
- [ ] `POST /patches/{patch}/notes` — admin tạo/cập nhật patch notes
- [ ] Structured format: buffs, nerfs, new champions, reworks, item changes
- [ ] Auto-detect champion stat changes qua data (so sánh win rate pre/post patch)
- [ ] "TL;DR" section — tóm tắt 3-5 điểm quan trọng nhất

## Post-Game Analysis — "What Went Wrong?"

- [ ] Analysis engine: so sánh comp/items/level với winner + meta
- [ ] Issue detection rules (weak comp, bad items, contested, late level...)
- [ ] Bilingual messages (VI + EN)
- [ ] `GET /player/{puuid}/matches/{match_id}/analysis` — phân tích 1 trận
- [ ] `GET /player/{puuid}/analysis/summary` — pattern recognition qua nhiều trận
- [ ] Celery task auto-analyze matches sau khi collect

## Vietnamese-First

- [ ] Tất cả analysis messages bilingual (VI + EN)
- [ ] Champion/item/augment names tiếng Việt (seed từ Riot VN localization)
- [ ] Guide content hỗ trợ tiếng Việt
- [ ] Patch notes tóm tắt tiếng Việt
- [ ] Error messages tiếng Việt

## Search

- [ ] Fuzzy search service (pg_trgm, typo tolerance)
- [ ] `GET /search` — tìm champion/item/augment
- [ ] `GET /search/suggest` — autocomplete top 5

## Matches

- [ ] `GET /matches/{id}` — chi tiết trận đấu
- [ ] `GET /matches/{id}/timeline` — event timeline

## Leaderboard

- [ ] Celery task cập nhật leaderboard mỗi 30 phút
- [ ] `GET /leaderboard` — top players theo region
- [ ] `GET /leaderboard/compositions` — top comps tuần này

## Cache

- [ ] Cache service (get/set helpers, key constants)
- [ ] Redis cache cho tất cả read endpoints
- [ ] X-Cache header trong response
- [ ] Cache invalidation sau recalculate

## Real-time

- [ ] `WS /ws/live/{puuid}` — live match tracking

## Auth & User Management

- [ ] Email/password registration + login (JWT)
- [ ] OAuth login (Google, Discord)
- [ ] Token refresh flow
- [ ] User profile (edit, link Riot account)
- [ ] API key management (create, list, revoke)
- [ ] Freemium tier system (free / premium)
- [ ] Subscription management (Stripe integration)
- [ ] Rate limiting per tier (Redis sliding window)
- [ ] X-RateLimit headers trong response
- [ ] Admin panel: manage users, roles, tiers, bans

## Production

- [ ] API key authentication + rate limiting per key
- [ ] Production startup validation (reject insecure config)
- [ ] Request ID middleware (tracing)
- [ ] Structured logging with request correlation
- [ ] Prometheus metrics + `/metrics` endpoint
- [ ] Multi-stage Dockerfile (dev / production)
- [ ] GitHub Actions CI/CD (test + lint + deploy)
- [ ] Deploy lên cloud (fly.io / Render)
- [ ] HTTPS-only enforcement
