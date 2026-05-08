# System Architecture — MetaScope API

## Overview

MetaScope API is designed with a **layered architecture** with clear separation between:
- **Ingestion layer**: Collects data from Riot API
- **Storage layer**: PostgreSQL (persistent) + Redis (cache/queue)
- **Business logic layer**: Services for computing stats, tier lists, search
- **API layer**: FastAPI exposes HTTP/WebSocket endpoints

---

## Data Flow

### Flow 1: Data Collection (Background)

```
Celery Beat Scheduler
        │  (every hour / every new patch)
        ▼
TFT Collector (app/collector/tft_collector.py)
        │
        ├──▶ RiotClient.get_tft_match_list(puuid)
        │           │ RIOT_REGIONAL_URL (sea.api.riotgames.com)
        │           │ TFT Match v1
        │           ▼
        │    [match_id_1, match_id_2, ...]
        │
        ├──▶ RiotClient.get_match_detail(match_id)  [concurrent, rate-limited]
        │           │ RIOT_REGIONAL_URL
        │           ▼
        │    Raw Riot JSON
        │
        ├──▶ Transformer.parse_match(raw_json)
        │           │
        │           ▼
        │    Normalized DB models
        │
        └──▶ PostgreSQL (INSERT OR IGNORE)
```

### Flow 2: Stats Calculation (Background)

```
Celery Beat (every hour)
        │
        ▼
calculate_champion_stats(patch)
        │
        ├──▶ Query match_participants + participant_units
        │    GROUP BY champion_id, patch
        │    → win_rate, top4_rate, avg_placement, pick_rate
        │
        ├──▶ compute_tier_score()
        │    → tier_score = wr*0.35 + placement*0.35 + pick_rate*0.30
        │
        ├──▶ INSERT INTO champion_stats (upsert)
        │
        └──▶ Redis SETEX tft:meta:tier:{patch}:ranked TTL=900
```

### Flow 2b: Detect & Calculate Comps (Background)

```
Celery Beat (every 2 hours)
        │
        ▼
detect_and_calculate_comps(patch)
        │
        ├──▶ Query match_participants (traits_active, units, items)
        │    WHERE patch = current AND comp NOT yet classified
        │
        ├──▶ Trait fingerprinting:
        │    traits_active → sort by tier DESC → hash
        │    → comp_hash (deduplication key)
        │
        ├──▶ UPSERT compositions (comp_hash, primary_traits, carry, units)
        │
        ├──▶ Calculate comp_stats:
        │    GROUP BY comp_hash, patch
        │    → win_rate, top4_rate, avg_placement, pick_rate
        │    → compute_tier_score() → assign tier
        │
        ├──▶ Calculate best augments/items per comp
        │    → JOIN participant augments + units.items GROUP BY comp
        │
        └──▶ Redis SETEX tft:meta:comps:{patch}:ranked TTL=900
```

### Flow 3: API Request

```
HTTP GET /api/v1/meta/tier-list?patch=14.10
        │
        ▼
FastAPI Route Handler (app/api/routes/meta.py)
        │
        ├──▶ Redis GET tft:meta:tier:14.10:ranked
        │    ├── HIT  → return cached (X-Cache: HIT header)
        │    └── MISS ─▶ TierListService.get_tier_list(db, patch, queue)
        │                       │
        │                       ▼
        │               SELECT FROM champion_stats
        │               WHERE patch = '14.10'
        │               ORDER BY tier_score DESC
        │                       │
        │                       ▼
        │               Redis SETEX (TTL 900s)
        │                       │
        │                       ▼
        └──▶ TierListResponse (JSON)
```

---

## Rate Limiting — Riot API

Development key limits:
- 20 requests / 1 second
- 100 requests / 2 minutes

Solution in `app/collector/riot_client.py`:

```
Request Queue
     │
     ▼
Token Bucket (20 tokens/s)
     │
     ├── Token available? → Execute request
     │
     └── No token? → asyncio.sleep(token_refresh_time)
                              │
                              ▼
                    asyncio.Semaphore(20)  ← max concurrent
                              │
                              ▼
                    httpx.AsyncClient
                              │
                    ┌─────────┴─────────┐
                    │  429 Received?    │
                    │  YES: sleep(Retry-After), retry
                    │  NO:  return response
                    └───────────────────┘
```

---

## Caching Strategy

| Data | Cache Key | TTL | Rationale |
|---|---|---|---|
| Tier list | `tft:meta:tier:{patch}:{queue}` | 15 min | Updated hourly, OK if stale for 15 min |
| Comp list | `tft:meta:comps:{patch}:{queue}` | 15 min | Same cadence as tier list |
| Comp detail | `tft:comp:{id}:stats:{patch}` | 1 hour | Rarely changes within a patch |
| Trait stats | `tft:trait:{name}:stats:{patch}` | 1 hour | Same cadence as champion stats |
| Item cheatsheet | `tft:items:cheatsheet:{set}` | 6 hours | Static data, updates each patch |
| Rolling odds | `tft:game:odds:{set}` | 6 hours | Static data |
| Guides list | `tft:guides:{sort}:{patch}:{page}` | 5 min | UGC changes frequently |
| Patch notes | `tft:patches:{patch}:notes` | 6 hours | Rarely changes after publish |
| Match analysis | `tft:analysis:{match_id}:{puuid}` | 24 hours | Results never change |
| Player analysis summary | `tft:analysis:summary:{puuid}:{patch}` | 30 min | Updates when new games are played |
| Champion stats | `tft:champion:{id}:stats:{patch}` | 1 hour | Rarely changes within a patch |
| Search results | `tft:search:{query_hash}` | 5 min | Expensive query, stable results |
| Player profile | `tft:player:{puuid}` | 30 min | Refreshes after each game |
| Leaderboard | `tft:leaderboard:{region}:{tier}` | 30 min | Update job every 30 min |
| Patch list | `tft:patches` | 6 hours | New patches are very rare |

Cache invalidation: Celery task automatically clears cache after recalculating stats.

---

## Database — Importance Tiers

### Hot data (frequently queried)
- `champion_stats` — tier list queries
- `players` — player lookup
- `matches` (recent) — match history

### Warm data (periodically queried)
- `match_participants` — stats calculation
- `participant_units` — item/comp analysis

### Cold data (rarely queried)
- `matches` (old patches) — historical comparison
- Raw match JSON is not stored, only normalized data

### TimescaleDB
The `champion_stats` and `item_stats` tables use TimescaleDB hypertable
partitioned by `calculated_at` (time column). This enables:
```sql
-- Query win rate over time (patch trend)
SELECT time_bucket('1 patch', calculated_at), avg(win_rate)
FROM champion_stats
WHERE champion_id = 'TFT13_Yone' AND calculated_at > NOW() - INTERVAL '3 months'
GROUP BY 1 ORDER BY 1;
```

---

## Background Jobs (Celery)

| Task | Schedule | Estimated Duration |
|---|---|---|
| `collect_new_matches` | Every 30 minutes | 5-10 min |
| `sync_player_profiles` | Every hour | 3-5 min |
| `calculate_champion_stats` | Every hour | 2-3 min |
| `calculate_item_stats` | Every hour | 1-2 min |
| `calculate_augment_stats` | Every 2 hours | 2-3 min |
| `detect_and_calculate_comps` | Every 2 hours | 5-10 min |
| `calculate_trait_stats` | Every 2 hours | 2-3 min |
| `update_leaderboard` | Every 30 minutes | 1-2 min |
| `refresh_champion_data` | On new patch | 1 min |
| `auto_detect_patch_changes` | On new patch | 3-5 min |
| `analyze_recent_matches` | Every 30 minutes (after collect) | 5-10 min |

Flower UI monitoring: `http://localhost:5555`

---

## Dependency Graph

```
main.py
  └── app/{domain}/router.py        ← HTTP interface
        └── app/core/dependencies.py (get_db, get_redis, get_current_user)
        └── app/{domain}/dependencies.py (feature-specific deps)
        └── app/{domain}/service.py  ← Business logic
              └── app/core/database.py
              └── app/core/redis.py
              └── app/{domain}/models.py

app/core/celery.py (autodiscover tasks)
  └── app/{domain}/jobs.py           ← Celery tasks
        └── app/{domain}/service.py
        └── app/ports/riot/client.py ← External API
        └── app/ports/riot/transformer.py
```

**Dependency rules:**
- `router.py` → `service.py` → `models.py` (top-down)
- No cross-imports between domains
- `ports/` may only be imported by `service.py` or `jobs.py`
- `core/` may be imported by any module

---

## Security Considerations

- API key in `X-API-Key` header, never in URL
- Rate limiting per API key using Redis sliding window
- `.env` is never committed (included in `.gitignore`)
- Riot API key is only used server-side, never exposed in responses
- 100% input validation via Pydantic schemas
- SQL injection is not possible because SQLAlchemy parameterized queries are used
