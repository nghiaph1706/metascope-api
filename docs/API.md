# API Reference — MetaScope API

Base URL: `http://localhost:8000/api/v1`  
Swagger UI: `http://localhost:8000/docs`  
ReDoc: `http://localhost:8000/redoc`

---

## Authentication

Hỗ trợ 2 phương thức:

### 1. JWT Token (cho users)

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

Lấy token qua `/auth/login` hoặc `/auth/oauth/{provider}`.

### 2. API Key (cho external developers)

```http
X-API-Key: msc_your_api_key_here
```

Tạo API key tại `/auth/api-keys`.

### Ký hiệu trong docs

- Không ký hiệu = public (anonymous OK)
- 🔑 = yêu cầu login (JWT hoặc API key)
- 👑 = yêu cầu premium tier
- 🛡️ = admin only

---

## Rate Limits

| Tier | Limit | Áp dụng cho |
|---|---|---|
| Anonymous | 30 req/min | IP-based |
| Free (logged in) | 60 req/min | Per user |
| Premium | 300 req/min | Per user |
| API Key (free) | 60 req/min | Per key |
| API Key (premium) | 300 req/min | Per key |
| Admin | Unlimited | — |

Headers trong response:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1705312260
```

Khi vượt limit → `429 Too Many Requests` với `Retry-After` header.

---

## Response Format

### Success

```json
{
  "data": { ... },
  "meta": {
    "cached": true,
    "cache_ttl": 847,
    "patch": "14.10"
  }
}
```

### Error

```json
{
  "error": "champion_not_found",
  "message": "Champion 'Yas' not found. Did you mean 'Yasuo'?",
  "details": {
    "suggestions": ["Yasuo", "Yae"]
  }
}
```

### Pagination

```json
{
  "data": [ ... ],
  "next_cursor": "eyJpZCI6IjEyMyJ9",
  "total": 250
}
```

---

## Endpoints

---

### System

#### `GET /health`

Health check tổng thể.

**Response 200**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "celery": "healthy"
  },
  "version": "1.0.0"
}
```

---

### Auth

#### `POST /auth/register`

Đăng ký tài khoản mới.

**Request Body**
```json
{
  "email": "player@example.com",
  "username": "player1",
  "password": "securepassword123",
  "display_name": "Player 1"
}
```

**Response 201**
```json
{
  "user": { "id": "...", "username": "player1", "tier": "free" },
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

---

#### `POST /auth/login`

Login bằng email + password.

**Request Body**
```json
{ "email": "player@example.com", "password": "securepassword123" }
```

**Response 200** — cùng format với register.

---

#### `GET /auth/oauth/{provider}`

Redirect tới OAuth provider (Google, Discord).

**Parameters**
| Tên | Mô tả |
|---|---|
| `provider` | `google` hoặc `discord` |

**Flow**: Redirect → Provider login → Callback → JWT token.

---

#### `POST /auth/refresh`

Refresh access token.

**Request Body**
```json
{ "refresh_token": "eyJhbGciOiJIUzI1NiIs..." }
```

---

#### `GET /auth/me` 🔑

Profile của user hiện tại.

**Response 200**
```json
{
  "id": "...",
  "email": "player@example.com",
  "username": "player1",
  "display_name": "Player 1",
  "role": "user",
  "tier": "free",
  "linked_puuid": "...",
  "oauth_providers": ["discord"],
  "usage_today": {
    "analysis_used": 2,
    "analysis_limit": 3,
    "comp_detail_used": 4,
    "comp_detail_limit": 5
  }
}
```

---

#### `PUT /auth/me` 🔑

Cập nhật profile.

---

#### `POST /auth/link-riot` 🔑

Liên kết tài khoản Riot. Verify bằng cách đặt icon chỉ định.

**Request Body**
```json
{ "game_name": "PlayerName", "tag_line": "VN2" }
```

---

#### `POST /auth/api-keys` 🔑

Tạo API key.

**Response 201**
```json
{
  "key": "msc_abc123def456...",
  "key_prefix": "msc_abc123",
  "name": "My App",
  "tier": "free",
  "note": "Đây là lần duy nhất key được hiển thị đầy đủ. Hãy lưu lại."
}
```

---

#### `GET /auth/api-keys` 🔑

List API keys (chỉ hiện prefix, không hiện full key).

---

#### `DELETE /auth/api-keys/{id}` 🔑

Revoke API key.

---

### Admin 🛡️

#### `GET /admin/users` 🛡️

List users (pagination, search).

---

#### `PUT /admin/users/{id}/role` 🛡️

Thay đổi role: user → moderator → admin.

---

#### `PUT /admin/users/{id}/tier` 🛡️

Grant/revoke premium.

---

#### `POST /admin/users/{id}/ban` 🛡️

Ban/unban user.

---

### Player

#### `GET /player/{region}/{game_name}/{tag_line}`

Lookup player theo region và Riot ID.

**Parameters**
| Tên | Vị trí | Type | Mô tả |
|---|---|---|---|
| `region` | path | string | Platform region: `vn2`, `kr`, `na1`, `euw1` |
| `game_name` | path | string | Tên game, ví dụ: `Faker` |
| `tag_line` | path | string | Tag, ví dụ: `KR1` hoặc `2611` |

**Response 200**
```json
{
  "data": {
    "puuid": "Cst5vZKHi4P...",
    "game_name": "Faker",
    "tag_line": "KR1",
    "region": "kr",
    "summoner_level": 854,
  "profile_icon_id": 5295,
  "last_updated": "2024-01-15T10:00:00Z"
}
```

**Errors**
- `404` — `player_not_found`: Player không tồn tại

---

#### `GET /player/{puuid}/matches`

Match history của player.

**Query Parameters**
| Tên | Default | Mô tả |
|---|---|---|
| `count` | 20 | Số match trả về, max 100 |
| `cursor` | null | Cursor cho trang tiếp theo |
| `queue` | null | Filter: `ranked`, `normal`, `double_up` |
| `patch` | null | Filter theo patch, ví dụ: `14.10` |

**Response 200**
```json
{
  "data": [
    {
      "match_id": "VN2_123456789",
      "placement": 1,
      "patch": "14.10",
      "game_datetime": "2024-01-15T09:30:00Z",
      "game_length": 1823,
      "level": 9,
      "augments": ["TFT13_Augment_SpellBlade2"],
      "traits": [
        { "name": "Void", "tier_current": 2, "tier_total": 3 }
      ]
    }
  ],
  "next_cursor": "eyJpZCI6Ijk4NyJ9",
  "total": 87
}
```

---

#### `GET /player/{puuid}/stats` 🔑

**Query Parameters**
| Tên | Default | Mô tả |
|---|---|---|
| `patch` | latest | Patch cụ thể hoặc `latest` |
| `games` | 20 | Số game tính toán |

**Response 200**
```json
{
  "puuid": "Cst5vZKHi4P...",
  "patch": "14.10",
  "games_analyzed": 20,
  "avg_placement": 3.45,
  "win_rate": 0.15,
  "top4_rate": 0.60,
  "top1_rate": 0.15
}
```

---

#### `GET /player/{puuid}/analysis` 🔑

Phân tích chi tiết: comp hay dùng, điểm mạnh/yếu.

**Response 200**
```json
{
  "puuid": "...",
  "analyzed_games": 20,
  "top_compositions": [
    {
      "traits": ["Void", "Challenger"],
      "games_played": 8,
      "avg_placement": 2.75,
      "win_rate": 0.25,
      "vs_server_avg": "+0.12"
    }
  ],
  "best_champions": [
    {
      "unit_id": "TFT13_Yone",
      "name": "Yone",
      "games": 12,
      "avg_placement": 2.3
    }
  ],
  "insights": [
    "Bạn thường chơi tốt hơn server average khi dùng Void synergy (+12% win rate)",
    "Augment Silver/Gold tier có hiệu quả cao hơn Prismatic với bạn"
  ]
}
```

---

### Meta & Analytics

#### `GET /meta/tier-list`

Tier list champion theo patch.

**Query Parameters**
| Tên | Default | Mô tả |
|---|---|---|
| `patch` | latest | Patch version hoặc `latest` |
| `queue` | ranked | `ranked` hoặc `normal` |

**Response 200**
```json
{
  "patch": "14.10",
  "queue": "ranked",
  "last_updated": "2024-01-15T09:00:00Z",
  "total_games_analyzed": 150420,
  "tiers": {
    "S": [
      {
        "champion_id": "TFT13_Yone",
        "name": "Yone",
        "cost": 4,
        "tier_score": 0.87,
        "win_rate": 0.142,
        "top4_rate": 0.623,
        "avg_placement": 3.12,
        "games_played": 8420,
        "trend": "up"
      }
    ],
    "A": [ ... ],
    "B": [ ... ],
    "C": [ ... ],
    "D": [ ... ]
  },
  "meta": { "cached": true, "cache_ttl": 634 }
}
```

---

#### `GET /meta/champions/{champion_id}/stats`

Stats chi tiết một champion.

**Query Parameters**
| Tên | Default | Mô tả |
|---|---|---|
| `patch` | latest | Patch version |
| `queue` | ranked | Queue type |

**Response 200**
```json
{
  "champion_id": "TFT13_Yone",
  "name": "Yone",
  "cost": 4,
  "patch": "14.10",
  "win_rate": 0.142,
  "top4_rate": 0.623,
  "avg_placement": 3.12,
  "games_played": 8420,
  "tier": "S",
  "tier_score": 0.87,
  "best_items": [
    { "item_id": "BFSword", "name": "B.F. Sword", "win_rate_boost": 0.08 }
  ],
  "best_traits": ["Void", "Challenger"],
  "patch_history": [
    { "patch": "14.9", "win_rate": 0.118, "tier": "A" },
    { "patch": "14.10", "win_rate": 0.142, "tier": "S" }
  ]
}
```

---

#### `GET /meta/items/{item_id}/stats`

Stats item — win rate tổng và theo từng champion.

**Response 200**
```json
{
  "item_id": "Bloodthirster",
  "name": "Bloodthirster",
  "patch": "14.10",
  "overall": {
    "win_rate": 0.138,
    "top4_rate": 0.591,
    "games_played": 45230
  },
  "best_champions": [
    {
      "champion_id": "TFT13_Yone",
      "name": "Yone",
      "win_rate": 0.162,
      "top4_rate": 0.651,
      "games_played": 3240
    }
  ]
}
```

---

#### `GET /meta/augments/{augment_id}/stats`

Stats augment theo tier và stage.

**Response 200**
```json
{
  "augment_id": "TFT13_Augment_SpellBlade2",
  "name": "Spellblade II",
  "tier": 2,
  "patch": "14.10",
  "win_rate": 0.155,
  "top4_rate": 0.612,
  "avg_placement": 3.05,
  "games_played": 12400,
  "by_stage": {
    "2-1": { "win_rate": 0.151, "games": 4200 },
    "3-2": { "win_rate": 0.158, "games": 5100 },
    "4-2": { "win_rate": 0.162, "games": 3100 }
  }
}
```

---

#### `GET /meta/compare` 🔑

So sánh meta giữa 2 patch.

**Query Parameters**
| Tên | Bắt buộc | Mô tả |
|---|---|---|
| `patch_a` | ✅ | Patch cũ hơn, ví dụ: `14.9` |
| `patch_b` | ✅ | Patch mới hơn, ví dụ: `14.10` |

**Response 200**
```json
{
  "patch_a": "14.9",
  "patch_b": "14.10",
  "biggest_risers": [
    { "name": "Yone", "tier_a": "B", "tier_b": "S", "win_rate_delta": +0.024 }
  ],
  "biggest_fallers": [
    { "name": "Kaisa", "tier_a": "S", "tier_b": "C", "win_rate_delta": -0.031 }
  ],
  "stable": [
    { "name": "Jinx", "tier_a": "A", "tier_b": "A", "win_rate_delta": +0.002 }
  ]
}
```

---

#### `GET /meta/patches`

Danh sách patches có dữ liệu.

**Response 200**
```json
{
  "patches": [
    { "patch": "14.10", "games_available": 150420, "is_current": true },
    { "patch": "14.9",  "games_available": 289100, "is_current": false }
  ]
}
```

---

### Compositions

#### `GET /meta/comps`

Top compositions theo patch, xếp hạng tier.

**Query Parameters**
| Tên | Default | Mô tả |
|---|---|---|
| `patch` | latest | Patch version hoặc `latest` |
| `queue` | ranked | `ranked` hoặc `normal` |
| `tier` | null | Filter theo tier: `S`, `A`, `B`, `C`, `D` |
| `limit` | 20 | Max results |

**Response 200**
```json
{
  "patch": "14.10",
  "queue": "ranked",
  "total_games_analyzed": 150420,
  "comps": [
    {
      "comp_id": "...",
      "name": "6 Void Yone Carry",
      "tier": "S",
      "tier_score": 0.89,
      "primary_traits": ["Void", "Challenger"],
      "primary_carry": "TFT13_Yone",
      "win_rate": 0.168,
      "top4_rate": 0.672,
      "avg_placement": 2.95,
      "pick_rate": 0.082,
      "games_played": 12340,
      "units": [
        {
          "unit_id": "TFT13_Yone",
          "name": "Yone",
          "cost": 4,
          "role": "carry",
          "priority": 1,
          "recommended_items": ["Bloodthirster", "GuinsoosRageblade", "HandOfJustice"]
        }
      ],
      "best_augments": [
        { "id": "TFT13_Augment_SpellBlade2", "name": "Spellblade II", "win_rate": 0.192 }
      ],
      "trend": "up"
    }
  ],
  "meta": { "cached": true, "cache_ttl": 634 }
}
```

---

#### `GET /meta/comps/{comp_id}`

Chi tiết một composition: units, items, augments, matchups.

**Response 200**
```json
{
  "comp_id": "...",
  "name": "6 Void Yone Carry",
  "tier": "S",
  "patch": "14.10",
  "win_rate": 0.168,
  "top4_rate": 0.672,
  "avg_placement": 2.95,
  "games_played": 12340,
  "units": [
    {
      "unit_id": "TFT13_Yone",
      "name": "Yone",
      "cost": 4,
      "role": "carry",
      "priority": 1,
      "recommended_items": ["Bloodthirster", "GuinsoosRageblade", "HandOfJustice"],
      "avg_star_level": 2.3
    }
  ],
  "best_augments_by_stage": {
    "2-1": [{ "id": "...", "name": "...", "win_rate": 0.18 }],
    "3-2": [{ "id": "...", "name": "...", "win_rate": 0.19 }],
    "4-2": [{ "id": "...", "name": "...", "win_rate": 0.21 }]
  },
  "trait_breakdown": [
    { "name": "Void", "active_tier": 3, "max_tier": 3 },
    { "name": "Challenger", "active_tier": 2, "max_tier": 3 }
  ],
  "patch_history": [
    { "patch": "14.9", "tier": "A", "win_rate": 0.142 },
    { "patch": "14.10", "tier": "S", "win_rate": 0.168 }
  ]
}
```

---

#### `GET /meta/comps/trending`

Comps đang tăng popularity hoặc win rate nhanh nhất so với tuần trước.

**Response 200**
```json
{
  "patch": "14.10",
  "trending_up": [
    {
      "comp_id": "...",
      "name": "6 Void Yone Carry",
      "win_rate_delta": +0.026,
      "pick_rate_delta": +0.015,
      "current_tier": "S",
      "previous_tier": "B"
    }
  ],
  "trending_down": [
    {
      "comp_id": "...",
      "name": "4 Sorcerer Kaisa Carry",
      "win_rate_delta": -0.031,
      "pick_rate_delta": -0.008,
      "current_tier": "C",
      "previous_tier": "A"
    }
  ]
}
```

---

### Traits / Synergies

#### `GET /meta/traits`

Danh sách traits với stats theo active tier.

**Query Parameters**
| Tên | Default | Mô tả |
|---|---|---|
| `patch` | latest | Patch version |
| `queue` | ranked | Queue type |

**Response 200**
```json
{
  "patch": "14.10",
  "traits": [
    {
      "name": "Void",
      "tiers": [
        { "active_tier": 2, "win_rate": 0.131, "top4_rate": 0.58, "avg_placement": 3.8, "games": 24500 },
        { "active_tier": 3, "win_rate": 0.168, "top4_rate": 0.67, "avg_placement": 2.95, "games": 12300 }
      ]
    }
  ]
}
```

---

#### `GET /meta/traits/{name}/stats`

Stats chi tiết một trait, per tier level, per patch.

**Response 200**
```json
{
  "name": "Void",
  "patch": "14.10",
  "tiers": [
    {
      "active_tier": 3,
      "win_rate": 0.168,
      "top4_rate": 0.67,
      "avg_placement": 2.95,
      "games_played": 12300,
      "best_champions": ["TFT13_Yone", "TFT13_Kaisa"],
      "best_augments": [{ "id": "...", "name": "...", "win_rate": 0.19 }]
    }
  ],
  "patch_history": [
    { "patch": "14.9", "tier_3_win_rate": 0.142 },
    { "patch": "14.10", "tier_3_win_rate": 0.168 }
  ]
}
```

---

### Items (Extended)

#### `GET /meta/items/cheatsheet`

Bảng craft: component A + B = item X.

**Response 200**
```json
{
  "components": [
    { "item_id": "BFSword", "name": "B.F. Sword" },
    { "item_id": "ChainVest", "name": "Chain Vest" }
  ],
  "recipes": [
    {
      "item_id": "Bloodthirster",
      "name": "Bloodthirster",
      "components": ["BFSword", "ChainVest"],
      "description": "Physical damage heals the holder",
      "stats": { "ad": 15, "armor": 25 }
    }
  ]
}
```

---

#### `GET /meta/items/{id}/best-holders`

Top champions dùng item này hiệu quả nhất.

**Response 200**
```json
{
  "item_id": "Bloodthirster",
  "name": "Bloodthirster",
  "patch": "14.10",
  "best_holders": [
    {
      "champion_id": "TFT13_Yone",
      "name": "Yone",
      "win_rate_with_item": 0.172,
      "win_rate_without_item": 0.138,
      "delta": +0.034,
      "games_with_item": 5200
    }
  ]
}
```

---

### Game Data (Static)

#### `GET /game/rolling-odds`

Tỷ lệ shop theo level.

**Response 200**
```json
{
  "tft_set": 13,
  "patch": "14.10",
  "odds": [
    { "level": 7, "cost_1": 19, "cost_2": 30, "cost_3": 35, "cost_4": 15, "cost_5": 1 },
    { "level": 8, "cost_1": 15, "cost_2": 20, "cost_3": 25, "cost_4": 30, "cost_5": 10 }
  ]
}
```

---

#### `GET /game/champions`

Danh sách champions với base stats cho set hiện tại.

---

#### `GET /game/items`

Danh sách items với recipes và stats.

---

#### `GET /game/augments`

Danh sách augments theo tier (Silver, Gold, Prismatic).

---

#### `GET /game/traits`

Danh sách traits với breakpoints (bao nhiêu units để activate tier nào).

---

### Guides (User-Generated Content)

#### `POST /guides` 🔑

Tạo guide mới. Yêu cầu authenticated user.

**Request Body**
```json
{
  "title": "Hướng dẫn chơi 6 Void Yone Carry",
  "content": "## Early game\n\nBắt đầu với...",
  "guide_type": "comp",
  "comp_id": "...",
  "patch": "14.10"
}
```

**Response 201**
```json
{
  "id": "...",
  "slug": "huong-dan-choi-6-void-yone-carry",
  "title": "Hướng dẫn chơi 6 Void Yone Carry",
  "author": { "id": "...", "username": "player1", "display_name": "Player 1" },
  "created_at": "2024-01-15T10:00:00Z"
}
```

---

#### `GET /guides`

List guides, sort theo votes hoặc thời gian.

**Query Parameters**
| Tên | Default | Mô tả |
|---|---|---|
| `sort` | votes | `votes`, `recent`, `views` |
| `patch` | null | Filter theo patch |
| `type` | null | `comp`, `general`, `item`, `beginner` |
| `comp_id` | null | Guides cho comp cụ thể |
| `limit` | 20 | Max results |
| `cursor` | null | Pagination |

**Response 200**
```json
{
  "data": [
    {
      "id": "...",
      "title": "Hướng dẫn chơi 6 Void Yone Carry",
      "slug": "huong-dan-choi-6-void-yone-carry",
      "guide_type": "comp",
      "author": { "username": "player1", "display_name": "Player 1" },
      "patch": "14.10",
      "upvotes": 42,
      "downvotes": 3,
      "view_count": 1250,
      "created_at": "2024-01-15T10:00:00Z"
    }
  ],
  "next_cursor": "..."
}
```

---

#### `GET /guides/{id}`

Đọc guide chi tiết (Markdown content).

---

#### `PUT /guides/{id}` 🔑

Edit guide. Chỉ author mới được edit.

---

#### `DELETE /guides/{id}` 🔑

Xóa guide. Author hoặc admin.

---

#### `POST /guides/{id}/vote` 🔑

Upvote hoặc downvote.

**Request Body**
```json
{ "vote": 1 }
```
`1` = upvote, `-1` = downvote, `0` = remove vote.

---

#### `POST /guides/{id}/comments` 🔑

Thêm comment.

**Request Body**
```json
{
  "content": "Guide rất hay, cảm ơn!",
  "parent_id": null
}
```

---

#### `GET /guides/{id}/comments`

List comments (threaded).

---

### Patch Notes

#### `GET /patches`

Danh sách patches có notes.

**Response 200**
```json
{
  "patches": [
    {
      "patch": "14.10",
      "title": "Patch 14.10 — Void nerfed, Sorcerer buffed",
      "published_at": "2024-05-15T00:00:00Z",
      "has_notes": true
    }
  ]
}
```

---

#### `GET /patches/{patch}/notes`

Patch notes chi tiết với tóm tắt.

**Response 200**
```json
{
  "patch": "14.10",
  "title": "Patch 14.10 — Void nerfed, Sorcerer buffed",
  "tldr": [
    "Void trait nerfed: tier 3 giảm damage 15%",
    "Sorcerer buffed: tier 2 thêm 10 AP",
    "Yone base AD giảm 5"
  ],
  "buffs": [
    { "champion_id": "TFT13_Ahri", "description": "Spell damage 250 → 280", "impact": "minor" }
  ],
  "nerfs": [
    { "champion_id": "TFT13_Yone", "description": "AD 75 → 70", "impact": "major" }
  ],
  "item_changes": [
    { "item_id": "Bloodthirster", "description": "Healing 25% → 20%", "impact": "moderate" }
  ],
  "trait_changes": [
    { "trait_name": "Void", "description": "3-piece bonus damage 35% → 30%", "impact": "major" }
  ],
  "auto_detected": {
    "biggest_winners": [
      { "name": "Ahri", "win_rate_before": 0.11, "win_rate_after": 0.14, "delta": +0.03 }
    ],
    "biggest_losers": [
      { "name": "Yone", "win_rate_before": 0.17, "win_rate_after": 0.14, "delta": -0.03 }
    ]
  },
  "published_at": "2024-05-15T00:00:00Z"
}
```

---

#### `POST /patches/{patch}/notes` 🛡️

Tạo hoặc cập nhật patch notes.

---

### Post-Game Analysis — "What Went Wrong?"

#### `GET /player/{puuid}/matches/{match_id}/analysis` 🔑

Phân tích chi tiết trận đấu: tại sao thua, nên làm gì khác. Bilingual (VI + EN).

**Response 200**
```json
{
  "match_id": "VN2_123456789",
  "puuid": "...",
  "placement": 5,
  "comp_played": {
    "name": "4 Sorcerer Kaisa Carry",
    "tier": "C",
    "meta_winrate": 0.082
  },
  "scores": {
    "comp_tier": "C",
    "items_optimal": 0.45,
    "winner_similarity": 0.32
  },
  "issues": [
    {
      "type": "weak_comp",
      "severity": "high",
      "message_vi": "Comp bạn chơi (4 Sorcerer) đang ở tier C với win rate 8.2%",
      "message_en": "Your comp (4 Sorcerer) is C-tier with 8.2% win rate"
    },
    {
      "type": "suboptimal_items",
      "severity": "medium",
      "message_vi": "Yone của bạn có Sunfire Cape — item này không hiệu quả trên carry AD",
      "message_en": "Your Yone has Sunfire Cape — ineffective on AD carries",
      "details": { "unit": "TFT13_Yone", "bad_item": "SunfireCape", "suggested": "Bloodthirster" }
    },
    {
      "type": "contested_comp",
      "severity": "medium",
      "message_vi": "3 người khác trong lobby cũng chơi Void — comp bị contested",
      "message_en": "3 other players also played Void — your comp was contested"
    }
  ],
  "strengths": [
    {
      "type": "good_augment",
      "message_vi": "Augment Spellblade II là lựa chọn tốt cho comp này (top 3 win rate)",
      "message_en": "Spellblade II is a strong augment pick for this comp (top 3 win rate)"
    }
  ],
  "suggestions": [
    {
      "type": "better_comp",
      "message_vi": "Với những tướng bạn có, comp 6 Void Yone Carry (tier S) sẽ hiệu quả hơn",
      "message_en": "With your champions, 6 Void Yone Carry (S-tier) would be more effective"
    },
    {
      "type": "better_items",
      "message_vi": "Thay Sunfire Cape bằng Bloodthirster trên Yone sẽ tăng ~3.4% win rate",
      "message_en": "Replacing Sunfire Cape with Bloodthirster on Yone would increase win rate by ~3.4%"
    }
  ],
  "comparison_with_winner": {
    "winner_placement": 1,
    "winner_comp": "6 Void Yone Carry",
    "winner_level": 9,
    "your_level": 7,
    "champion_overlap": 3,
    "item_overlap": 1
  }
}
```

---

#### `GET /player/{puuid}/analysis/summary` 👑

Tổng hợp issues thường gặp qua nhiều trận — pattern recognition.

**Query Parameters**
| Tên | Default | Mô tả |
|---|---|---|
| `games` | 20 | Số game phân tích |
| `patch` | latest | Patch |

**Response 200**
```json
{
  "puuid": "...",
  "games_analyzed": 20,
  "avg_placement": 4.2,
  "recurring_issues": [
    {
      "type": "suboptimal_items",
      "frequency": 14,
      "message_vi": "Bạn thường xuyên đặt sai items (14/20 trận). Hãy check best-in-slot trước khi craft",
      "message_en": "You frequently use suboptimal items (14/20 games). Check best-in-slot before crafting"
    },
    {
      "type": "contested_comp",
      "frequency": 8,
      "message_vi": "Bạn hay force comp dù bị contested (8/20 trận). Hãy scout và linh hoạt pivot",
      "message_en": "You often force comps when contested (8/20 games). Scout and be ready to pivot"
    }
  ],
  "improvement_tips_vi": [
    "Ưu tiên #1: Cải thiện item choices — đây là vấn đề lớn nhất",
    "Ưu tiên #2: Học cách scout lobby và pivot khi comp bị contested"
  ],
  "improvement_tips_en": [
    "Priority #1: Improve item choices — this is your biggest issue",
    "Priority #2: Learn to scout the lobby and pivot when your comp is contested"
  ]
}
```

---

### Search

#### `GET /search`

Fuzzy search tướng, trang bị, augment.

**Query Parameters**
| Tên | Default | Mô tả |
|---|---|---|
| `q` | (bắt buộc) | Search query, ví dụ: `yas`, `BF sword` |
| `type` | all | `champion`, `item`, `augment`, hoặc `all` |
| `limit` | 10 | Max results, max 30 |

**Response 200**
```json
{
  "query": "yas",
  "results": [
    {
      "type": "champion",
      "id": "TFT13_Yasuo",
      "name": "Yasuo",
      "score": 0.92,
      "data": { "cost": 4, "traits": ["Void", "Challenger"] }
    },
    {
      "type": "champion",
      "id": "TFT13_Yae",
      "name": "Yae Miko",
      "score": 0.61,
      "data": { "cost": 3, "traits": ["Invoker"] }
    }
  ],
  "total": 2
}
```

---

#### `GET /search/suggest`

Autocomplete — top 5 suggestions nhanh.

**Query Parameters**
| Tên | Mô tả |
|---|---|
| `q` | Partial query, ít nhất 2 ký tự |

**Response 200**
```json
{
  "suggestions": [
    { "id": "TFT13_Yasuo", "name": "Yasuo", "type": "champion" },
    { "id": "TFT13_Yae",   "name": "Yae Miko", "type": "champion" }
  ]
}
```

---

### Leaderboard

#### `GET /leaderboard`

Top players theo region và tier.

**Query Parameters**
| Tên | Default | Mô tả |
|---|---|---|
| `region` | vn2 | Region code: `vn2`, `kr`, `euw1`, ... |
| `tier` | challenger | `challenger`, `grandmaster`, `master` |
| `limit` | 50 | Max results |
| `cursor` | null | Pagination cursor |

**Response 200**
```json
{
  "data": [
    {
      "rank": 1,
      "puuid": "...",
      "game_name": "PlayerName",
      "tag_line": "VN2",
      "lp": 1842,
      "wins": 145,
      "losses": 89,
      "avg_placement": 2.91
    }
  ],
  "next_cursor": "...",
  "updated_at": "2024-01-15T10:15:00Z"
}
```

---

#### `GET /leaderboard/compositions`

Top compositions tuần này theo win rate.

**Response 200**
```json
{
  "data": [
    {
      "rank": 1,
      "traits": ["Void", "Challenger"],
      "key_champions": ["Yone", "Kaisa"],
      "win_rate": 0.18,
      "top4_rate": 0.67,
      "games_played": 8420
    }
  ]
}
```

---

### Matches

#### `GET /matches/{match_id}`

Chi tiết đầy đủ một trận đấu.

**Response 200**
```json
{
  "match_id": "VN2_123456789",
  "patch": "14.10",
  "game_datetime": "2024-01-15T09:30:00Z",
  "game_length": 1823,
  "participants": [
    {
      "placement": 1,
      "game_name": "Winner",
      "tag_line": "VN2",
      "level": 9,
      "gold_left": 12,
      "augments": ["TFT13_Augment_SpellBlade2"],
      "traits": [{ "name": "Void", "tier_current": 3 }],
      "units": [
        {
          "unit_id": "TFT13_Yone",
          "name": "Yone",
          "tier": 2,
          "items": ["Bloodthirster", "GuinsoosRageblade"]
        }
      ]
    }
  ]
}
```

---

#### `GET /matches/{match_id}/timeline` 🔑

Event timeline trong trận.

---

#### `WebSocket /ws/live/{puuid}` 🔑

Live match tracking — nhận push notification khi match kết thúc.

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/live/{puuid}');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // data.type: "match_completed" | "ping" | "error"
};
```

---

## HTTP Status Codes

| Code | Ý nghĩa |
|---|---|
| 200 | Success |
| 400 | Bad request (invalid params) |
| 401 | Missing API key |
| 403 | Invalid API key |
| 404 | Resource not found |
| 422 | Validation error (wrong type) |
| 429 | Rate limit exceeded |
| 503 | Service unavailable (DB/Redis down) |
