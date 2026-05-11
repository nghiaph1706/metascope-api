# Features — MetaScope API

List of features, in priority order. Check `[x]` when complete.

---

## Core Infrastructure

- [x] Docker Compose stack runs (API + Postgres + Redis + Celery)
- [x] Core layer: `database.py`, `redis.py`, `logging.py`
- [x] Alembic setup + initial migration (enable pg_trgm, TimescaleDB)
- [x] SQLAlchemy models: Player, Match, Champion, Item, Augment
- [x] Seed script: champions + items from DataDragon
- [ ] Multi-region data collection (VN2, KR, EUW, NA...)

## Data Collection

- [x] Riot API client (`riot_client.py`)
  - Token bucket rate limiter (20 req/s, 100 req/2min)
  - asyncio.Semaphore for concurrent limit
  - Retry with exponential backoff on 429
- [x] Transformer: parse Riot JSON → DB models
- [ ] TFT Collector: fetch → deduplicate → batch insert
- [ ] Sync player profiles (periodic job, resolve puuid → player info)
- [ ] Celery worker + beat scheduler
- [ ] Collect data from multiple regions (configurable region list)

## Player

- [x] `GET /player/{region}/{game_name}/{tag_line}` — lookup player
- [ ] `GET /player/{puuid}/matches` — match history (cursor pagination)
- [ ] `GET /player/{puuid}/stats` — aggregated stats
- [ ] `GET /player/{puuid}/analysis` — frequently used comps, strengths/weaknesses

## Meta & Analytics

- [ ] Stats calculation service (champion, item, augment stats)
- [ ] Tier list algorithm (`win_rate*0.35 + placement*0.35 + pick_rate*0.30`)
- [ ] `GET /meta/tier-list` — tier list by patch
- [ ] `GET /meta/champions/{id}/stats` — detailed champion stats
- [ ] `GET /meta/items/{id}/stats` — item stats
- [ ] `GET /meta/augments/{id}/stats` — augment stats
- [ ] `GET /meta/compare` — compare 2 patches
- [ ] `GET /meta/patches` — list of patches with data

## Compositions

- [ ] Comp detection algorithm (trait-based fingerprinting from match data)
- [ ] Comp stats calculation (win rate, top4, placement, pick rate per comp)
- [ ] Best augments/items per comp (per-stage breakdown)
- [ ] `GET /meta/comps` — top comps by patch, ranked by tier
- [ ] `GET /meta/comps/{id}` — comp detail: units, items, augments, history
- [ ] `GET /meta/comps/trending` — comps rising/falling the most
- [ ] Celery task `detect_and_calculate_comps` (every 2 hours)

## Traits / Synergies

- [ ] `GET /meta/traits` — list of traits with stats (win rate, avg placement per active tier)
- [ ] `GET /meta/traits/{id}/stats` — detailed trait stats (per tier level, per patch)
- [ ] Trait combo analysis: is trait X + trait Y effective together

## Items

- [ ] `GET /meta/items/cheatsheet` — craft table: component A + B = item X
- [ ] `GET /meta/items/{id}/best-holders` — top champions using this item most effectively
- [ ] Item recommendation per champion + per comp

## Game Data (Static)

- [ ] `GET /game/rolling-odds` — shop odds by level (seeded from Riot static data)
- [ ] `GET /game/champions` — list of champions with base stats
- [ ] `GET /game/items` — list of items with recipes
- [ ] `GET /game/augments` — list of augments by tier
- [ ] `GET /game/traits` — list of traits with breakpoints
- [ ] Auto-update on new patch (Celery task checks DataDragon)

## Guides (User-Generated Content)

- [ ] User registration + authentication (email/password or OAuth)
- [ ] `POST /guides` — create new guide (comp guide, how-to-play)
- [ ] `GET /guides` — list guides (sort by votes, recency, patch)
- [ ] `GET /guides/{id}` — read detailed guide
- [ ] `PUT /guides/{id}` — edit guide (author only)
- [ ] `DELETE /guides/{id}` — delete guide (author or admin)
- [ ] `POST /guides/{id}/vote` — upvote/downvote
- [ ] `POST /guides/{id}/comments` — comment on guide
- [ ] `GET /guides/{id}/comments` — list comments (threaded)
- [ ] Link guide to composition (optional)
- [ ] Markdown support for guide content
- [ ] Filter guides by patch, comp, author

## Patch Notes

- [ ] `GET /patches` — list of patches
- [ ] `GET /patches/{patch}/notes` — summarized patch notes
- [ ] `POST /patches/{patch}/notes` — admin creates/updates patch notes
- [ ] Structured format: buffs, nerfs, new champions, reworks, item changes
- [ ] Auto-detect champion stat changes via data (compare win rate pre/post patch)
- [ ] "TL;DR" section — summary of the 3-5 most important points

## Post-Game Analysis — "What Went Wrong?"

- [ ] Analysis engine: compare comp/items/level with winner + meta
- [ ] Issue detection rules (weak comp, bad items, contested, late level...)
- [ ] Bilingual messages (VI + EN)
- [ ] `GET /player/{puuid}/matches/{match_id}/analysis` — analyze a single match
- [ ] `GET /player/{puuid}/analysis/summary` — pattern recognition across multiple matches
- [ ] Celery task to auto-analyze matches after collection

## Vietnamese-First

- [ ] All analysis messages bilingual (VI + EN)
- [ ] Champion/item/augment names in Vietnamese (seeded from Riot VN localization)
- [ ] Guide content supports Vietnamese
- [ ] Patch notes summary in Vietnamese
- [ ] Error messages in Vietnamese

## Search

- [ ] Fuzzy search service (pg_trgm, typo tolerance)
- [ ] `GET /search` — search champion/item/augment
- [ ] `GET /search/suggest` — autocomplete top 5

## Matches

- [ ] `GET /matches/{id}` — match details
- [ ] `GET /matches/{id}/timeline` — event timeline

## Leaderboard

- [ ] Celery task to update leaderboard every 30 minutes
- [ ] `GET /leaderboard` — top players by region
- [ ] `GET /leaderboard/compositions` — top comps this week

## Cache

- [ ] Cache service (get/set helpers, key constants)
- [ ] Redis cache for all read endpoints
- [ ] X-Cache header in response
- [ ] Cache invalidation after recalculate

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
- [ ] X-RateLimit headers in response
- [ ] Admin panel: manage users, roles, tiers, bans

## Production

- [ ] API key authentication + rate limiting per key
- [ ] Production startup validation (reject insecure config)
- [ ] Request ID middleware (tracing)
- [ ] Structured logging with request correlation
- [ ] Prometheus metrics + `/metrics` endpoint
- [ ] Multi-stage Dockerfile (dev / production)
- [ ] GitHub Actions CI/CD (test + lint + deploy)
- [ ] Deploy to cloud (fly.io / Render)
- [ ] HTTPS-only enforcement
