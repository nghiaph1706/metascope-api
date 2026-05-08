# Kiến trúc Hệ thống — MetaScope API

## Tổng quan

MetaScope API được thiết kế theo **layered architecture** với tách biệt rõ ràng giữa:
- **Ingestion layer**: Thu thập data từ Riot API
- **Storage layer**: PostgreSQL (persistent) + Redis (cache/queue)
- **Business logic layer**: Services tính toán stats, tier list, search
- **API layer**: FastAPI expose HTTP/WebSocket endpoints

---

## Data Flow

### Flow 1: Thu thập data (Background)

```
Celery Beat Scheduler
        │  (mỗi giờ / mỗi patch mới)
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

### Flow 2: Tính Stats (Background)

```
Celery Beat (mỗi giờ)
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
Celery Beat (mỗi 2 giờ)
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

Giải pháp trong `app/collector/riot_client.py`:

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

| Data | Cache Key | TTL | Lý do |
|---|---|---|---|
| Tier list | `tft:meta:tier:{patch}:{queue}` | 15 phút | Cập nhật mỗi giờ, OK nếu stale 15p |
| Comp list | `tft:meta:comps:{patch}:{queue}` | 15 phút | Cùng cadence với tier list |
| Comp detail | `tft:comp:{id}:stats:{patch}` | 1 giờ | Ít thay đổi trong patch |
| Trait stats | `tft:trait:{name}:stats:{patch}` | 1 giờ | Cùng cadence với champion stats |
| Item cheatsheet | `tft:items:cheatsheet:{set}` | 6 giờ | Static data, update mỗi patch |
| Rolling odds | `tft:game:odds:{set}` | 6 giờ | Static data |
| Guides list | `tft:guides:{sort}:{patch}:{page}` | 5 phút | UGC thay đổi thường xuyên |
| Patch notes | `tft:patches:{patch}:notes` | 6 giờ | Ít thay đổi sau publish |
| Match analysis | `tft:analysis:{match_id}:{puuid}` | 24 giờ | Kết quả không đổi |
| Player analysis summary | `tft:analysis:summary:{puuid}:{patch}` | 30 phút | Cập nhật khi có game mới |
| Champion stats | `tft:champion:{id}:stats:{patch}` | 1 giờ | Ít thay đổi trong patch |
| Search results | `tft:search:{query_hash}` | 5 phút | Query đắt, kết quả ổn định |
| Player profile | `tft:player:{puuid}` | 30 phút | Fresh sau mỗi game |
| Leaderboard | `tft:leaderboard:{region}:{tier}` | 30 phút | Update job mỗi 30p |
| Patch list | `tft:patches` | 6 giờ | Patch mới rất hiếm |

Cache invalidation: Celery task tự xóa cache sau khi recalculate stats.

---

## Database — Phân tầng quan trọng

### Hot data (query thường xuyên)
- `champion_stats` — tier list queries
- `players` — player lookup
- `matches` (recent) — match history

### Warm data (query định kỳ)
- `match_participants` — stats calculation
- `participant_units` — item/comp analysis

### Cold data (query hiếm)
- `matches` (old patches) — historical comparison
- Raw match JSON không lưu, chỉ lưu normalized

### TimescaleDB
Bảng `champion_stats` và `item_stats` dùng TimescaleDB hypertable
partition theo `calculated_at` (time column). Cho phép:
```sql
-- Query win rate over time (patch trend)
SELECT time_bucket('1 patch', calculated_at), avg(win_rate)
FROM champion_stats
WHERE champion_id = 'TFT13_Yone' AND calculated_at > NOW() - INTERVAL '3 months'
GROUP BY 1 ORDER BY 1;
```

---

## Background Jobs (Celery)

| Task | Schedule | Thời gian ước tính |
|---|---|---|
| `collect_new_matches` | Mỗi 30 phút | 5–10 phút |
| `sync_player_profiles` | Mỗi giờ | 3–5 phút |
| `calculate_champion_stats` | Mỗi giờ | 2–3 phút |
| `calculate_item_stats` | Mỗi giờ | 1–2 phút |
| `calculate_augment_stats` | Mỗi 2 giờ | 2–3 phút |
| `detect_and_calculate_comps` | Mỗi 2 giờ | 5–10 phút |
| `calculate_trait_stats` | Mỗi 2 giờ | 2–3 phút |
| `update_leaderboard` | Mỗi 30 phút | 1–2 phút |
| `refresh_champion_data` | Khi có patch mới | 1 phút |
| `auto_detect_patch_changes` | Khi có patch mới | 3–5 phút |
| `analyze_recent_matches` | Mỗi 30 phút (sau collect) | 5–10 phút |

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

**Quy tắc dependency:**
- `router.py` → `service.py` → `models.py` (top-down)
- Không import chéo giữa domains
- `ports/` chỉ được import bởi `service.py` hoặc `jobs.py`
- `core/` được import bởi mọi module

---

## Security Considerations

- API key trong header `X-API-Key`, không bao giờ trong URL
- Rate limiting per API key bằng Redis sliding window
- `.env` không bao giờ commit (có trong `.gitignore`)
- Riot API key chỉ dùng server-side, không expose ra response
- Input validation 100% qua Pydantic schemas
- SQL injection không thể vì dùng SQLAlchemy parameterized queries
