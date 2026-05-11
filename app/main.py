"""FastAPI application entry point.

Initializes the app, registers middleware and routers.
See AGENTS.md for conventions and patterns.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.core.config import settings
from app.core.database import check_db_connection, close_db_engine
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
from app.core.logging import get_logger, setup_logging
from app.core.redis import check_redis_connection, close_redis_client
from app.match.router import router as match_router
from app.player.router import router as player_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifecycle manager: startup and shutdown."""
    setup_logging()
    log = get_logger("metascope")
    settings.validate_production()
    await check_db_connection()
    await check_redis_connection()
    log.info("startup_complete", environment=settings.environment)
    yield
    await close_db_engine()
    await close_redis_client()
    log.info("shutdown_complete")


app = FastAPI(
    title="MetaScope API",
    description="TFT Meta Analytics & Player Lookup System",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(PlayerNotFoundError)
async def player_not_found_handler(request: Request, exc: PlayerNotFoundError) -> ORJSONResponse:
    """Return 404 when player is not found."""
    return ORJSONResponse(
        status_code=404,
        content={"error": "player_not_found", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(ChampionNotFoundError)
async def champion_not_found_handler(
    request: Request, exc: ChampionNotFoundError
) -> ORJSONResponse:
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


app.include_router(player_router, prefix="/api/v1", tags=["Player"])
app.include_router(match_router, prefix="/api/v1", tags=["Matches"])


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, Any]:
    """Health check endpoint.

    Returns:
        Dict with the app's status and version.
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.environment,
    }
