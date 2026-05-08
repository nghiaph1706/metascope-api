"""FastAPI application entry point.

Khởi tạo app, đăng ký middleware và routers.
Xem AGENTS.md để biết convention và patterns.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifecycle manager: chạy startup và shutdown tasks."""
    settings.validate_production()
    # TODO: await check_db_connection()
    # TODO: await check_redis_connection()
    yield
    # TODO: await close_db_engine()
    # TODO: await close_redis_client()


app = FastAPI(
    title="MetaScope API",
    description="TFT Meta Analytics & Player Lookup System",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    default_response_class=ORJSONResponse,  # faster JSON serialization
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception Handlers ────────────────────────────────────────────

from app.core.exceptions import (
    AugmentNotFoundError,
    ChampionNotFoundError,
    CompositionNotFoundError,
    ForbiddenError,
    GuideNotFoundError,
    InsufficientDataError,
    InvalidPatchError,
    ItemNotFoundError,
    MatchNotFoundError,
    MetaScopeError,
    PlayerNotFoundError,
    PremiumRequiredError,
    RateLimitExceededError,
    RiotAPIError,
    RiotAPIKeyInvalidError,
    RiotRateLimitError,
    TraitNotFoundError,
    UnauthorizedError,
    UserBannedError,
    UserNotFoundError,
)


@app.exception_handler(PlayerNotFoundError)
async def player_not_found_handler(request: Request, exc: PlayerNotFoundError) -> ORJSONResponse:
    """Trả 404 khi player không tìm thấy."""
    return ORJSONResponse(
        status_code=404,
        content={"error": "player_not_found", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(ChampionNotFoundError)
async def champion_not_found_handler(request: Request, exc: ChampionNotFoundError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=404,
        content={"error": "champion_not_found", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(MatchNotFoundError)
async def match_not_found_handler(request: Request, exc: MatchNotFoundError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=404,
        content={"error": "match_not_found", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(ItemNotFoundError)
async def item_not_found_handler(request: Request, exc: ItemNotFoundError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=404,
        content={"error": "item_not_found", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(GuideNotFoundError)
async def guide_not_found_handler(request: Request, exc: GuideNotFoundError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=404,
        content={"error": "guide_not_found", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(CompositionNotFoundError)
async def comp_not_found_handler(request: Request, exc: CompositionNotFoundError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=404,
        content={"error": "composition_not_found", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(AugmentNotFoundError)
async def augment_not_found_handler(request: Request, exc: AugmentNotFoundError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=404,
        content={"error": "augment_not_found", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(TraitNotFoundError)
async def trait_not_found_handler(request: Request, exc: TraitNotFoundError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=404,
        content={"error": "trait_not_found", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(UserNotFoundError)
async def user_not_found_handler(request: Request, exc: UserNotFoundError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=404,
        content={"error": "user_not_found", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(InvalidPatchError)
async def invalid_patch_handler(request: Request, exc: InvalidPatchError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=404,
        content={"error": "invalid_patch", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(InsufficientDataError)
async def insufficient_data_handler(request: Request, exc: InsufficientDataError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=422,
        content={"error": "insufficient_data", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(UnauthorizedError)
async def unauthorized_handler(request: Request, exc: UnauthorizedError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=401,
        content={"error": "unauthorized", "message": exc.message},
    )


@app.exception_handler(ForbiddenError)
async def forbidden_handler(request: Request, exc: ForbiddenError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=403,
        content={"error": "forbidden", "message": exc.message},
    )


@app.exception_handler(PremiumRequiredError)
async def premium_required_handler(request: Request, exc: PremiumRequiredError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=403,
        content={"error": "premium_required", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(UserBannedError)
async def user_banned_handler(request: Request, exc: UserBannedError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=403,
        content={"error": "user_banned", "message": exc.message},
    )


@app.exception_handler(RateLimitExceededError)
async def rate_limit_handler(request: Request, exc: RateLimitExceededError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=429,
        content={"error": "rate_limit_exceeded", "message": exc.message, "details": exc.details},
        headers={"Retry-After": str(exc.retry_after)},
    )


@app.exception_handler(RiotRateLimitError)
async def riot_rate_limit_handler(request: Request, exc: RiotRateLimitError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=503,
        content={"error": "riot_rate_limit", "message": exc.message},
        headers={"Retry-After": str(exc.retry_after or 1)},
    )


@app.exception_handler(RiotAPIKeyInvalidError)
async def riot_key_invalid_handler(request: Request, exc: RiotAPIKeyInvalidError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=503,
        content={"error": "riot_api_key_invalid", "message": exc.message},
    )


@app.exception_handler(RiotAPIError)
async def riot_api_handler(request: Request, exc: RiotAPIError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=502,
        content={"error": "riot_api_error", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(MetaScopeError)
async def generic_error_handler(request: Request, exc: MetaScopeError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": exc.message, "details": exc.details},
    )


# ── Routers ───────────────────────────────────────────────────────
# TODO: uncomment khi tạo từng route file

# from app.api.routes import auth, admin, player, meta, guides, patches, game, search, leaderboard, matches, system
# app.include_router(system.router, tags=["System"])
# app.include_router(auth.router, prefix="/auth", tags=["Auth"])
# app.include_router(admin.router, prefix="/admin", tags=["Admin"])
# app.include_router(player.router, prefix="/api/v1", tags=["Player"])
# app.include_router(meta.router, prefix="/api/v1/meta", tags=["Meta"])
# app.include_router(guides.router, prefix="/api/v1/guides", tags=["Guides"])
# app.include_router(patches.router, prefix="/api/v1/patches", tags=["Patches"])
# app.include_router(game.router, prefix="/api/v1/game", tags=["Game"])
# app.include_router(search.router, prefix="/api/v1", tags=["Search"])
# app.include_router(leaderboard.router, prefix="/api/v1", tags=["Leaderboard"])
# app.include_router(matches.router, prefix="/api/v1", tags=["Matches"])


# ── Temporary health endpoint (remove after system.router is ready) ──

@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Dict với status và version của app.
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.environment,
    }
