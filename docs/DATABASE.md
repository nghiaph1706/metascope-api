# Database Schema — MetaScope API

## Setup

```bash
# Khởi tạo DB (chạy 1 lần)
make migrate

# Seed champion/item data
make seed

# Reset hoàn toàn (dev only)
make db-reset
```

---

## Schema Tổng quan

```
players ──────────────────────────────────────────────────┐
                                                           │ (soft ref, periodic sync)
matches ──────────────────────────────────────────────────┤
    │                                                      │
    └── match_participants ──────────────────── puuid ─────┘
              │
              └── participant_units
                        │── unit_id (soft ref → champions)
                        └── items[] (TEXT array, soft ref → items)

champions ── traits TEXT[] (array of trait names)
traits (static game data, breakpoints)
items
augments (standalone)

compositions ── comp_units ── unit_id (soft ref → champions)

champion_stats    ← TimescaleDB hypertable (calculated_at), partitioned by set
item_stats        ← TimescaleDB hypertable (calculated_at), partitioned by set
comp_stats        ← TimescaleDB hypertable (calculated_at), partitioned by set
trait_stats       ← TimescaleDB hypertable (calculated_at)
augment_stats     ← TimescaleDB hypertable (calculated_at)

users ── oauth_accounts, subscriptions, api_keys
guides ── guide_votes, guide_comments
match_analyses
patch_notes
localizations
```

---

## Bảng Chi Tiết

### `players`

```sql
CREATE TABLE players (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    puuid       VARCHAR(78) UNIQUE NOT NULL,   -- Riot PUUID, unique globally
    game_name   VARCHAR(50) NOT NULL,
    tag_line    VARCHAR(10) NOT NULL,
    region      VARCHAR(10) NOT NULL DEFAULT 'vn2',
    summoner_id VARCHAR(100),                  -- Legacy Summoner ID
    account_id  VARCHAR(100),
    profile_icon_id INT,
    summoner_level  INT,
    last_fetched_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_players_puuid ON players(puuid);
CREATE INDEX idx_players_game_name_tag ON players(game_name, tag_line);
```

### `matches`

```sql
CREATE TABLE matches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id        VARCHAR(30) UNIQUE NOT NULL,  -- Ví dụ: VN2_123456789
    patch           VARCHAR(10) NOT NULL,          -- Ví dụ: 14.10
    patch_major     SMALLINT NOT NULL,             -- 14
    patch_minor     SMALLINT NOT NULL,             -- 10
    game_datetime   TIMESTAMPTZ NOT NULL,
    game_length     INT NOT NULL,                  -- Seconds
    game_variation  VARCHAR(50),                   -- normal, ranked, double_up...
    queue_id        INT,
    tft_set_number  INT,
    tft_set_core_name VARCHAR(50),
    region          VARCHAR(10) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_matches_match_id ON matches(match_id);
CREATE INDEX idx_matches_patch ON matches(patch);
CREATE INDEX idx_matches_game_datetime ON matches(game_datetime DESC);
CREATE INDEX idx_matches_patch_datetime ON matches(patch, game_datetime DESC);
```

### `match_participants`

```sql
CREATE TABLE match_participants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id        UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    puuid           VARCHAR(78) NOT NULL,  -- Không FK → players, dùng periodic sync job
    placement       SMALLINT NOT NULL CHECK (placement BETWEEN 1 AND 8),
    level           SMALLINT NOT NULL,
    gold_left       SMALLINT NOT NULL DEFAULT 0,
    last_round      SMALLINT,
    players_eliminated INT DEFAULT 0,
    total_damage_to_players INT DEFAULT 0,
    augments        TEXT[] DEFAULT '{}',          -- Array of augment IDs
    traits_active   JSONB DEFAULT '[]',           -- [{name, tier_current, tier_total}]
    time_eliminated DECIMAL(8,2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mp_match_id ON match_participants(match_id);
CREATE INDEX idx_mp_puuid ON match_participants(puuid);
CREATE INDEX idx_mp_placement ON match_participants(placement);
-- Composite index cho stats queries
CREATE INDEX idx_mp_match_puuid ON match_participants(match_id, puuid);
```

### `participant_units`

```sql
CREATE TABLE participant_units (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id  UUID NOT NULL REFERENCES match_participants(id) ON DELETE CASCADE,
    unit_id         VARCHAR(100) NOT NULL,  -- Riot unit ID, e.g. TFT13_Yone
    tier            SMALLINT NOT NULL DEFAULT 1,  -- 1, 2, 3 sao
    rarity          SMALLINT,               -- Cost tier
    items           TEXT[] DEFAULT '{}',   -- Array of item IDs
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pu_participant_id ON participant_units(participant_id);
CREATE INDEX idx_pu_unit_id ON participant_units(unit_id);
-- Dùng cho item-on-champion stats
CREATE INDEX idx_pu_unit_items ON participant_units USING GIN(items);
```

### `champions`

```sql
CREATE TABLE champions (
    unit_id         VARCHAR(100) PRIMARY KEY,  -- e.g. TFT13_Yone
    name            VARCHAR(100) NOT NULL,
    cost            SMALLINT NOT NULL,
    traits          TEXT[] DEFAULT '{}',
    ability_name    VARCHAR(100),
    ability_desc    TEXT,
    stats           JSONB DEFAULT '{}',         -- base stats từ DataDragon
    tft_set_number  INT NOT NULL,
    patch_added     VARCHAR(10),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- pg_trgm fuzzy search index
CREATE INDEX idx_champion_name_trgm ON champions USING GIN (name gin_trgm_ops);
CREATE INDEX idx_champion_cost ON champions(cost);
CREATE INDEX idx_champion_traits ON champions USING GIN(traits);
```

### `items`

```sql
CREATE TABLE items (
    item_id         VARCHAR(100) PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    icon            VARCHAR(200),
    is_component    BOOLEAN NOT NULL DEFAULT FALSE,
    is_craftable    BOOLEAN NOT NULL DEFAULT FALSE,
    is_embleme      BOOLEAN NOT NULL DEFAULT FALSE,
    is_spatula      BOOLEAN NOT NULL DEFAULT FALSE,
    composition     TEXT[] DEFAULT '{}',         -- Component item IDs
    stats           JSONB DEFAULT '{}',
    tft_set_number  INT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_item_name_trgm ON items USING GIN (name gin_trgm_ops);
CREATE INDEX idx_item_is_craftable ON items(is_craftable) WHERE is_craftable = TRUE;
```

### `augments`

```sql
CREATE TABLE augments (
    augment_id      VARCHAR(100) PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    tier            SMALLINT NOT NULL DEFAULT 1,  -- 1=Silver, 2=Gold, 3=Prismatic
    icon            VARCHAR(200),
    tft_set_number  INT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_augment_name_trgm ON augments USING GIN (name gin_trgm_ops);
CREATE INDEX idx_augment_tier ON augments(tier);
```

### `traits`

Static data — trait breakpoints, descriptions. Seed từ DataDragon.

```sql
CREATE TABLE traits (
    trait_id         VARCHAR(100) PRIMARY KEY,       -- e.g. "Void", "Challenger"
    name             VARCHAR(100) NOT NULL,
    description      TEXT,
    tft_set_number   INT NOT NULL,
    breakpoints      JSONB NOT NULL DEFAULT '[]',    -- [{min_units: 2, style: 1}, {min_units: 4, style: 2}]
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_trait_name_trgm ON traits USING GIN(name gin_trgm_ops);
CREATE INDEX idx_trait_set ON traits(tft_set_number);
```

### `champion_stats` (TimescaleDB hypertable)

```sql
CREATE TABLE champion_stats (
    champion_id     VARCHAR(100) NOT NULL REFERENCES champions(unit_id),
    tft_set_number  INT NOT NULL,
    patch           VARCHAR(10) NOT NULL,
    queue_type      VARCHAR(20) NOT NULL DEFAULT 'ranked',
    games_played    INT NOT NULL DEFAULT 0,
    wins            INT NOT NULL DEFAULT 0,
    top4s           INT NOT NULL DEFAULT 0,
    total_placement DECIMAL(10,2) NOT NULL DEFAULT 0,
    win_rate        DECIMAL(5,4),    -- computed: wins / games_played
    top4_rate       DECIMAL(5,4),    -- computed: top4s / games_played
    avg_placement   DECIMAL(4,2),    -- computed: total_placement / games_played
    pick_rate       DECIMAL(5,4),    -- computed: games_played / total_games_in_patch
    tier_score      DECIMAL(5,4),    -- wr*0.35 + placement_score*0.35 + pick_rate*0.30
    tier            CHAR(1),         -- S, A, B, C, D
    calculated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (champion_id, tft_set_number, patch, queue_type, calculated_at)
);

-- TimescaleDB: partition by calculated_at (time column)
SELECT create_hypertable('champion_stats', 'calculated_at');

CREATE INDEX idx_cs_champion_patch ON champion_stats(champion_id, patch, queue_type);
CREATE INDEX idx_cs_tier_score ON champion_stats(patch, tier_score DESC);
```

### `item_stats` (TimescaleDB hypertable)

```sql
CREATE TABLE item_stats (
    item_id         VARCHAR(100) NOT NULL REFERENCES items(item_id),
    champion_id     VARCHAR(100) NOT NULL DEFAULT '_overall',  -- '_overall' = stats tổng, không FK vì sentinel value
    tft_set_number  INT NOT NULL,
    patch           VARCHAR(10) NOT NULL,
    queue_type      VARCHAR(20) NOT NULL DEFAULT 'ranked',
    games_played    INT NOT NULL DEFAULT 0,
    win_rate        DECIMAL(5,4),
    top4_rate       DECIMAL(5,4),
    avg_placement   DECIMAL(4,2),
    calculated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (item_id, champion_id, tft_set_number, patch, queue_type, calculated_at)
);

SELECT create_hypertable('item_stats', 'calculated_at');
```

### `augment_stats` (TimescaleDB hypertable)

```sql
CREATE TABLE augment_stats (
    augment_id      VARCHAR(100) NOT NULL REFERENCES augments(augment_id),
    tft_set_number  INT NOT NULL,
    patch           VARCHAR(10) NOT NULL,
    queue_type      VARCHAR(20) NOT NULL DEFAULT 'ranked',
    stage           VARCHAR(10) NOT NULL DEFAULT '_all',  -- '2-1', '3-2', '4-2'; '_all' = overall
    games_played    INT NOT NULL DEFAULT 0,
    win_rate        DECIMAL(5,4),
    top4_rate       DECIMAL(5,4),
    avg_placement   DECIMAL(4,2),
    calculated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (augment_id, tft_set_number, patch, queue_type, stage, calculated_at)
);

SELECT create_hypertable('augment_stats', 'calculated_at');

CREATE INDEX idx_as_augment_patch ON augment_stats(augment_id, patch, queue_type);
```

### `compositions`

Mỗi composition là một nhóm champions + traits đặc trưng, được detect tự động từ match data.

```sql
CREATE TABLE compositions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comp_hash       VARCHAR(64) UNIQUE NOT NULL,   -- hash từ sorted unit_ids → deduplicate
    name            VARCHAR(100),                   -- auto-generated hoặc manual: "6 Void Yone Carry"
    tft_set_number  INT NOT NULL,
    primary_traits  TEXT[] NOT NULL DEFAULT '{}',   -- ["Void", "Challenger"]
    primary_carry   VARCHAR(100),                   -- unit_id của carry chính
    unit_count      SMALLINT NOT NULL,              -- số units trong comp (thường 7-9)
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_comp_hash ON compositions(comp_hash);
CREATE INDEX idx_comp_set ON compositions(tft_set_number);
CREATE INDEX idx_comp_traits ON compositions USING GIN(primary_traits);
CREATE INDEX idx_comp_name_trgm ON compositions USING GIN(name gin_trgm_ops);
```

### `comp_units`

Champions trong mỗi composition, với vai trò và items khuyến nghị.

```sql
CREATE TABLE comp_units (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comp_id         UUID NOT NULL REFERENCES compositions(id) ON DELETE CASCADE,
    unit_id         VARCHAR(100) NOT NULL REFERENCES champions(unit_id),
    role            VARCHAR(20) NOT NULL DEFAULT 'flex',  -- 'carry', 'tank', 'support', 'flex'
    priority        SMALLINT NOT NULL DEFAULT 2,    -- 1=core, 2=standard, 3=flex slot
    recommended_items TEXT[] DEFAULT '{}',           -- top 3 items cho unit này trong comp
    avg_star_level  DECIMAL(3,2),                   -- avg tier khi comp wins
    UNIQUE (comp_id, unit_id)
);

CREATE INDEX idx_cu_comp_id ON comp_units(comp_id);
CREATE INDEX idx_cu_unit_id ON comp_units(unit_id);
```

### `comp_stats` (TimescaleDB hypertable)

Stats tổng hợp cho mỗi composition theo patch.

```sql
CREATE TABLE comp_stats (
    comp_id         UUID NOT NULL REFERENCES compositions(id),
    tft_set_number  INT NOT NULL,
    patch           VARCHAR(10) NOT NULL,
    queue_type      VARCHAR(20) NOT NULL DEFAULT 'ranked',
    games_played    INT NOT NULL DEFAULT 0,
    wins            INT NOT NULL DEFAULT 0,
    top4s           INT NOT NULL DEFAULT 0,
    total_placement DECIMAL(10,2) NOT NULL DEFAULT 0,
    win_rate        DECIMAL(5,4),
    top4_rate       DECIMAL(5,4),
    avg_placement   DECIMAL(4,2),
    pick_rate       DECIMAL(5,4),
    tier_score      DECIMAL(5,4),
    tier            CHAR(1),                        -- S, A, B, C, D
    best_augments   JSONB DEFAULT '[]',             -- top 3 augments [{id, name, win_rate}]
    best_items      JSONB DEFAULT '{}',             -- per-unit best items {unit_id: [{item, wr}]}
    calculated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (comp_id, tft_set_number, patch, queue_type, calculated_at)
);

SELECT create_hypertable('comp_stats', 'calculated_at');

CREATE INDEX idx_cst_comp_patch ON comp_stats(comp_id, patch, queue_type);
CREATE INDEX idx_cst_tier_score ON comp_stats(patch, tier_score DESC);
```

---

## Composition Detection — Thuật toán

Match data → comp detection sử dụng **trait-based clustering**:

```
1. Từ mỗi match_participant, lấy traits_active (tier >= 2)
2. Sort traits theo tier DESC → tạo "trait fingerprint"
   Ví dụ: ["Void:3", "Challenger:2"] → fingerprint
3. Hash fingerprint → comp_hash
4. Nếu comp_hash đã tồn tại → link participant tới comp
5. Nếu comp_hash mới → tạo composition mới:
   - primary_traits = traits có tier cao nhất
   - primary_carry = unit có nhiều items nhất + cost cao nhất
   - name = auto-generate: "{trait_count} {trait_name} {carry_name} Carry"
6. Comps với games_played < min_sample_size bị filter khỏi API
```

---

## Trait Stats

### `trait_stats` (TimescaleDB hypertable)

```sql
CREATE TABLE trait_stats (
    trait_id        VARCHAR(100) NOT NULL REFERENCES traits(trait_id),
    active_tier     SMALLINT NOT NULL,              -- tier level đang active (1, 2, 3, 4)
    tft_set_number  INT NOT NULL,
    patch           VARCHAR(10) NOT NULL,
    queue_type      VARCHAR(20) NOT NULL DEFAULT 'ranked',
    games_played    INT NOT NULL DEFAULT 0,
    wins            INT NOT NULL DEFAULT 0,
    top4s           INT NOT NULL DEFAULT 0,
    total_placement DECIMAL(10,2) NOT NULL DEFAULT 0,
    win_rate        DECIMAL(5,4),
    top4_rate       DECIMAL(5,4),
    avg_placement   DECIMAL(4,2),
    calculated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (trait_id, active_tier, tft_set_number, patch, queue_type, calculated_at)
);

SELECT create_hypertable('trait_stats', 'calculated_at');

CREATE INDEX idx_ts_trait_patch ON trait_stats(trait_id, patch, queue_type);
```

---

## Static Game Data

### `rolling_odds`

Tỷ lệ shop theo level — seed từ Riot static data, update mỗi patch.

```sql
CREATE TABLE rolling_odds (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tft_set_number  INT NOT NULL,
    patch           VARCHAR(10) NOT NULL,
    level           SMALLINT NOT NULL CHECK (level BETWEEN 1 AND 10),
    cost_1_pct      DECIMAL(5,2) NOT NULL,          -- % chance 1-cost
    cost_2_pct      DECIMAL(5,2) NOT NULL,
    cost_3_pct      DECIMAL(5,2) NOT NULL,
    cost_4_pct      DECIMAL(5,2) NOT NULL,
    cost_5_pct      DECIMAL(5,2) NOT NULL,
    UNIQUE (tft_set_number, patch, level)
);
```

---

## User Management & Permissions

### `users`

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    username        VARCHAR(50) UNIQUE NOT NULL,
    password_hash   VARCHAR(255),                   -- NULL nếu chỉ dùng OAuth
    display_name    VARCHAR(100),
    avatar_url      VARCHAR(500),
    role            VARCHAR(20) NOT NULL DEFAULT 'user',  -- 'user', 'moderator', 'admin'
    tier            VARCHAR(20) NOT NULL DEFAULT 'free',  -- 'free', 'premium', 'admin'
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    linked_puuid    VARCHAR(78),                    -- optional: liên kết tài khoản Riot
    email_verified  BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_tier ON users(tier);
```

### `oauth_accounts`

Liên kết user với OAuth providers (Google, Discord).

```sql
CREATE TABLE oauth_accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider        VARCHAR(20) NOT NULL,           -- 'google', 'discord'
    provider_id     VARCHAR(255) NOT NULL,           -- ID từ provider
    provider_email  VARCHAR(255),
    provider_data   JSONB DEFAULT '{}',              -- avatar, display name, etc.
    access_token    VARCHAR(500),                    -- encrypted
    refresh_token   VARCHAR(500),                    -- encrypted
    token_expires_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider, provider_id)
);

CREATE INDEX idx_oauth_user ON oauth_accounts(user_id);
CREATE INDEX idx_oauth_provider ON oauth_accounts(provider, provider_id);
```

### `subscriptions`

Quản lý premium tier — khi nào bắt đầu, khi nào hết hạn.

```sql
CREATE TABLE subscriptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tier            VARCHAR(20) NOT NULL,            -- 'premium'
    status          VARCHAR(20) NOT NULL DEFAULT 'active',  -- 'active', 'cancelled', 'expired'
    payment_provider VARCHAR(20),                    -- 'stripe', 'manual', 'promo'
    payment_id      VARCHAR(255),                    -- Stripe subscription ID
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,                     -- NULL = lifetime
    cancelled_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sub_user ON subscriptions(user_id);
CREATE INDEX idx_sub_status ON subscriptions(status) WHERE status = 'active';
```

### `api_keys`

API keys cho external developers (phase 4).

```sql
CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash        VARCHAR(255) UNIQUE NOT NULL,    -- SHA-256 hash, never store raw
    key_prefix      VARCHAR(10) NOT NULL,            -- "msc_abc..." cho identification
    name            VARCHAR(100),                    -- "My App", "Testing"
    tier            VARCHAR(20) NOT NULL DEFAULT 'free',  -- 'free', 'premium', 'unlimited'
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at    TIMESTAMPTZ,
    request_count   BIGINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ak_user ON api_keys(user_id);
CREATE INDEX idx_ak_hash ON api_keys(key_hash);
CREATE INDEX idx_ak_prefix ON api_keys(key_prefix);
```

---

## Permission Matrix — Freemium Model

### Tiers

| Feature | Anonymous | Free (logged in) | Premium | Admin |
|---|---|---|---|---|
| **Meta** | | | | |
| Tier list | ✅ | ✅ | ✅ | ✅ |
| Champion stats (basic) | ✅ | ✅ | ✅ | ✅ |
| Champion stats (patch history) | ❌ | 3 patches | Unlimited | ✅ |
| Comp list | ✅ | ✅ | ✅ | ✅ |
| Comp detail | ❌ | 5/ngày | Unlimited | ✅ |
| Trait stats | ✅ | ✅ | ✅ | ✅ |
| Item cheatsheet | ✅ | ✅ | ✅ | ✅ |
| Meta compare (2 patches) | ❌ | ❌ | ✅ | ✅ |
| **Player** | | | | |
| Player lookup | ✅ | ✅ | ✅ | ✅ |
| Match history | 5 games | 20 games | Unlimited | ✅ |
| Player stats | ❌ | ✅ | ✅ | ✅ |
| **Analysis** | | | | |
| Post-game analysis (per match) | ❌ | 3/ngày | Unlimited | ✅ |
| Analysis summary (patterns) | ❌ | ❌ | ✅ | ✅ |
| **Community** | | | | |
| Read guides | ✅ | ✅ | ✅ | ✅ |
| Write guides | ❌ | ✅ | ✅ | ✅ |
| Vote/comment | ❌ | ✅ | ✅ | ✅ |
| **Patch Notes** | ✅ | ✅ | ✅ | ✅ |
| **Search** | ✅ | ✅ | ✅ | ✅ |
| **Leaderboard** | ✅ | ✅ | ✅ | ✅ |
| **API** | | | | |
| API rate limit | 30 req/min | 60 req/min | 300 req/min | Unlimited |
| API key creation | ❌ | 1 key | 5 keys | Unlimited |
| WebSocket live | ❌ | ❌ | ✅ | ✅ |

### Role Permissions (Moderation)

| Action | user | moderator | admin |
|---|---|---|---|
| Edit own guides | ✅ | ✅ | ✅ |
| Delete own guides | ✅ | ✅ | ✅ |
| Edit any guide | ❌ | ✅ | ✅ |
| Delete any guide | ❌ | ✅ | ✅ |
| Delete comments | ❌ | ✅ | ✅ |
| Ban users | ❌ | ❌ | ✅ |
| Manage patch notes | ❌ | ❌ | ✅ |
| Manage API keys (all) | ❌ | ❌ | ✅ |
| Grant premium | ❌ | ❌ | ✅ |

---

## User-Generated Content

### `guides`

```sql
CREATE TABLE guides (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id       UUID NOT NULL REFERENCES users(id),
    title           VARCHAR(200) NOT NULL,
    slug            VARCHAR(250) UNIQUE NOT NULL,   -- URL-friendly: "6-void-yone-carry-guide"
    content         TEXT NOT NULL,                   -- Markdown
    guide_type      VARCHAR(20) NOT NULL DEFAULT 'comp',  -- 'comp', 'general', 'item', 'beginner'
    comp_id         UUID REFERENCES compositions(id),      -- optional: link tới comp
    patch           VARCHAR(10) NOT NULL,
    tft_set_number  INT NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'published',  -- 'draft', 'published', 'archived'
    upvotes         INT NOT NULL DEFAULT 0,
    downvotes       INT NOT NULL DEFAULT 0,
    view_count      INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_guides_author ON guides(author_id);
CREATE INDEX idx_guides_comp ON guides(comp_id);
CREATE INDEX idx_guides_patch ON guides(patch);
CREATE INDEX idx_guides_status ON guides(status) WHERE status = 'published';
CREATE INDEX idx_guides_votes ON guides(upvotes DESC) WHERE status = 'published';
CREATE INDEX idx_guides_title_trgm ON guides USING GIN(title gin_trgm_ops);
```

### `guide_votes`

```sql
CREATE TABLE guide_votes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guide_id        UUID NOT NULL REFERENCES guides(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id),
    vote            SMALLINT NOT NULL CHECK (vote IN (-1, 1)),  -- -1 = downvote, 1 = upvote
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (guide_id, user_id)
);

CREATE INDEX idx_gv_guide ON guide_votes(guide_id);
```

### `guide_comments`

```sql
CREATE TABLE guide_comments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guide_id        UUID NOT NULL REFERENCES guides(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id),
    parent_id       UUID REFERENCES guide_comments(id),  -- NULL = top-level, non-null = reply
    content         TEXT NOT NULL,
    is_deleted      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_gc_guide ON guide_comments(guide_id);
CREATE INDEX idx_gc_parent ON guide_comments(parent_id) WHERE parent_id IS NOT NULL;
```

---

## Patch Notes

### `patch_notes`

```sql
CREATE TABLE patch_notes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patch           VARCHAR(10) UNIQUE NOT NULL,
    tft_set_number  INT NOT NULL,
    title           VARCHAR(200),                    -- "Patch 14.10 — Void nerfed, Sorcerer buffed"
    tldr            TEXT,                             -- 3-5 bullet points tóm tắt
    content         TEXT,                             -- Markdown đầy đủ
    buffs           JSONB DEFAULT '[]',               -- [{champion_id, description, impact}]
    nerfs           JSONB DEFAULT '[]',
    adjustments     JSONB DEFAULT '[]',
    new_champions   JSONB DEFAULT '[]',
    item_changes    JSONB DEFAULT '[]',
    trait_changes   JSONB DEFAULT '[]',
    system_changes  JSONB DEFAULT '[]',              -- rolling odds, leveling, etc.
    auto_detected   JSONB DEFAULT '{}',              -- auto-generated: win rate changes pre/post patch
    published_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pn_patch ON patch_notes(patch);
```

---

## Leaderboard

### `leaderboard_entries`

Snapshot leaderboard — cập nhật mỗi 30 phút từ Riot League API.

```sql
CREATE TABLE leaderboard_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    region          VARCHAR(10) NOT NULL,            -- 'vn2', 'kr', 'euw1'
    tier            VARCHAR(20) NOT NULL,            -- 'challenger', 'grandmaster', 'master'
    puuid           VARCHAR(78) NOT NULL,
    summoner_name   VARCHAR(100),
    lp              INT NOT NULL DEFAULT 0,
    wins            INT NOT NULL DEFAULT 0,
    losses          INT NOT NULL DEFAULT 0,
    rank_position   INT NOT NULL,                    -- 1 = top
    snapshot_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (region, tier, puuid, snapshot_at)
);

CREATE INDEX idx_lb_region_tier ON leaderboard_entries(region, tier, snapshot_at DESC);
CREATE INDEX idx_lb_puuid ON leaderboard_entries(puuid);
CREATE INDEX idx_lb_lp ON leaderboard_entries(region, tier, lp DESC);
```

---

## Post-Game Analysis — "What Went Wrong?"

### `match_analyses`

Phân tích tự động cho mỗi participant trong trận — so sánh với meta và với người thắng.

```sql
CREATE TABLE match_analyses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id        UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    puuid           VARCHAR(78) NOT NULL,
    placement       SMALLINT NOT NULL,

    -- So sánh với winner cùng trận
    winner_comp_similarity  DECIMAL(4,3),       -- 0.0–1.0: board của bạn giống winner bao nhiêu
    winner_item_overlap     SMALLINT,            -- số items trùng với winner carry

    -- So sánh với meta
    comp_tier               CHAR(1),             -- tier comp đã chơi (S/A/B/C/D/UNKNOWN)
    comp_meta_winrate       DECIMAL(5,4),        -- meta win rate của comp đã chơi
    items_optimal_score     DECIMAL(4,3),        -- 0.0–1.0: items tốt đến mức nào so với best-in-slot

    -- Insights (auto-generated)
    issues          JSONB NOT NULL DEFAULT '[]',  -- [{type, severity, message_vi, message_en, details}]
    strengths       JSONB NOT NULL DEFAULT '[]',  -- [{type, message_vi, message_en, details}]
    suggestions     JSONB NOT NULL DEFAULT '[]',  -- [{type, message_vi, message_en, details}]

    -- Meta
    analysis_version SMALLINT NOT NULL DEFAULT 1,
    calculated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (match_id, puuid)
);

CREATE INDEX idx_ma_match ON match_analyses(match_id);
CREATE INDEX idx_ma_puuid ON match_analyses(puuid);
CREATE INDEX idx_ma_puuid_time ON match_analyses(puuid, calculated_at DESC);
```

### Issue types (trong JSONB `issues`)

```json
[
  {
    "type": "weak_comp",
    "severity": "high",
    "message_vi": "Comp bạn chơi (4 Sorcerer) đang ở tier C với win rate 8.2%",
    "message_en": "Your comp (4 Sorcerer) is C-tier with 8.2% win rate",
    "details": { "comp_tier": "C", "comp_winrate": 0.082 }
  },
  {
    "type": "suboptimal_items",
    "severity": "medium",
    "message_vi": "Yone của bạn có Sunfire Cape — item này không hiệu quả trên carry AD",
    "message_en": "Your Yone has Sunfire Cape — this item is ineffective on AD carries",
    "details": { "unit": "TFT13_Yone", "bad_item": "SunfireCape", "suggested": "Bloodthirster" }
  },
  {
    "type": "contested_comp",
    "severity": "medium",
    "message_vi": "3 người khác trong lobby cũng chơi Void — comp bị contested",
    "message_en": "3 other players in the lobby also played Void — your comp was contested",
    "details": { "trait": "Void", "players_count": 3 }
  },
  {
    "type": "late_level",
    "severity": "low",
    "message_vi": "Bạn kết thúc ở level 7 — người thắng ở level 9. Cân nhắc leveling sớm hơn",
    "message_en": "You finished at level 7 — winner was level 9. Consider leveling earlier",
    "details": { "your_level": 7, "winner_level": 9 }
  }
]
```

### Analysis algorithm

```
1. Lấy match details + tất cả participants
2. Xác định comp mỗi participant (reuse comp detection)
3. Với mỗi participant (focus vào người request):
   a. Comp analysis:
      - Lookup comp_stats → tier, win_rate
      - Đếm bao nhiêu người cùng lobby chơi comp giống/tương tự (contested)
   b. Item analysis:
      - Với mỗi unit có items → lookup best-in-slot từ item_stats
      - Score = % items trùng với best-in-slot
      - Flag items không hợp (tank item trên carry, v.v.)
   c. Comparison với winner (#1 placement):
      - Overlap champions, traits, items
      - Level difference
      - Gold efficiency
   d. Generate issues/strengths/suggestions dựa trên rules:
      - comp_tier <= C → "weak_comp" issue
      - items_optimal_score < 0.5 → "suboptimal_items"
      - contested count >= 3 → "contested_comp"
      - level diff >= 2 vs winner → "late_level"
      - win_rate > meta avg → strength "strong_comp"
```

---

## Localization (Vietnamese-First)

### `localizations`

Tên tiếng Việt cho champions, items, augments, traits — seed từ Riot VN localization data.

```sql
CREATE TABLE localizations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type     VARCHAR(20) NOT NULL,           -- 'champion', 'item', 'augment', 'trait'
    entity_id       VARCHAR(100) NOT NULL,           -- FK tương ứng
    locale          VARCHAR(10) NOT NULL DEFAULT 'vi',  -- 'vi', 'en'
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    UNIQUE (entity_type, entity_id, locale)
);

CREATE INDEX idx_loc_entity ON localizations(entity_type, entity_id);
CREATE INDEX idx_loc_name_trgm ON localizations USING GIN(name gin_trgm_ops);
```

---

## Migrations — Quy tắc

```bash
# Tạo migration mới (sau khi thay đổi SQLAlchemy model)
alembic revision --autogenerate -m "add augment_stats table"

# Xem lịch sử migration
alembic history --verbose

# Upgrade lên version mới nhất
alembic upgrade head

# Downgrade 1 version
alembic downgrade -1

# Downgrade về trạng thái ban đầu (xóa hết)
alembic downgrade base
```

### Quy tắc đặt tên migration

Dùng Alembic autogenerate mặc định. Message mô tả rõ ràng:

```bash
alembic revision --autogenerate -m "create players table"
alembic revision --autogenerate -m "add trgm indexes"
alembic revision --autogenerate -m "add champion stats hypertable"
```

### Migration KHÔNG được chứa

- Business logic
- Data transformation phức tạp
- Queries không liên quan đến schema

---

## Useful Queries

```sql
-- Tier list gần nhất cho patch
SELECT c.name, cs.tier_score, cs.tier, cs.win_rate, cs.top4_rate, cs.avg_placement
FROM champion_stats cs
JOIN champions c ON cs.champion_id = c.unit_id
WHERE cs.patch = '14.10' AND cs.queue_type = 'ranked'
  AND cs.calculated_at = (
    SELECT MAX(calculated_at) FROM champion_stats WHERE patch = '14.10'
  )
ORDER BY cs.tier_score DESC;

-- Best items trên một champion
SELECT i.name, is_.win_rate, is_.top4_rate, is_.games_played
FROM item_stats is_
JOIN items i ON is_.item_id = i.item_id
WHERE is_.champion_id = 'TFT13_Yone' AND is_.patch = '14.10'
  AND is_.games_played >= 50
ORDER BY is_.win_rate DESC
LIMIT 5;

-- Fuzzy search champion
SELECT name, similarity(name, 'yone') AS score
FROM champions
WHERE name % 'yone' AND is_active = TRUE
ORDER BY score DESC
LIMIT 5;

-- Win rate trend qua các patch (TimescaleDB)
SELECT patch, AVG(win_rate) as avg_win_rate
FROM champion_stats
WHERE champion_id = 'TFT13_Yone'
  AND queue_type = 'ranked'
  AND calculated_at > NOW() - INTERVAL '90 days'
GROUP BY patch
ORDER BY patch;
```
