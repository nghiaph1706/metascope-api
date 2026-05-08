"""Custom exception hierarchy for the MetaScope API.

All app exceptions inherit from MetaScopeError.
Route handlers catch these exceptions and return appropriate HTTP responses.
"""


class MetaScopeError(Exception):
    """Base exception for the entire application."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        """Initialize exception with a message and optional details.

        Args:
            message: Human-readable error message.
            details: Dict containing additional context, included in the response.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ── Riot API Errors ───────────────────────────────────────────────

class RiotAPIError(MetaScopeError):
    """Error when calling the Riot Games API."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retry_after: int | None = None,
    ) -> None:
        """Initialize RiotAPIError.

        Args:
            message: Error description.
            status_code: HTTP status code from the Riot API, if available.
            retry_after: Number of seconds to wait before retrying (for 429).
        """
        super().__init__(message, {"status_code": status_code})
        self.status_code = status_code
        self.retry_after = retry_after


class RiotRateLimitError(RiotAPIError):
    """Riot API rate limit exceeded (429)."""

    def __init__(self, retry_after: int = 1) -> None:
        """Initialize with the retry_after header value.

        Args:
            retry_after: Number of seconds to wait, from the Retry-After header.
        """
        super().__init__(
            f"Riot API rate limit exceeded. Retry after {retry_after}s.",
            status_code=429,
            retry_after=retry_after,
        )


class RiotAPIKeyInvalidError(RiotAPIError):
    """Riot API key is invalid or expired (403)."""

    def __init__(self) -> None:
        super().__init__(
            "Riot API key is invalid or expired. Please renew at developer.riotgames.com.",
            status_code=403,
        )


# ── Player Errors ─────────────────────────────────────────────────

class PlayerNotFoundError(MetaScopeError):
    """Player does not exist in the Riot system."""

    def __init__(self, game_name: str, tag_line: str) -> None:
        """Initialize with Riot ID.

        Args:
            game_name: The player's game name.
            tag_line: The player's tag.
        """
        super().__init__(
            f"Player '{game_name}#{tag_line}' not found.",
            {"game_name": game_name, "tag_line": tag_line},
        )


# ── Match Errors ──────────────────────────────────────────────────

class MatchNotFoundError(MetaScopeError):
    """Match ID does not exist in the DB."""

    def __init__(self, match_id: str) -> None:
        """Initialize with match ID.

        Args:
            match_id: Riot match ID, e.g. VN2_123456789.
        """
        super().__init__(
            f"Match '{match_id}' not found.",
            {"match_id": match_id},
        )


# ── Champion / Item Errors ────────────────────────────────────────

class ChampionNotFoundError(MetaScopeError):
    """Champion ID does not exist in the DB."""

    def __init__(self, champion_id: str, suggestions: list[str] | None = None) -> None:
        """Initialize with champion ID and suggestions from fuzzy search.

        Args:
            champion_id: Champion unit ID or name.
            suggestions: List of suggested names, if available.
        """
        details: dict = {"champion_id": champion_id}
        if suggestions:
            details["suggestions"] = suggestions
        super().__init__(
            f"Champion '{champion_id}' not found.",
            details,
        )


class ItemNotFoundError(MetaScopeError):
    """Item ID does not exist in the DB."""

    def __init__(self, item_id: str) -> None:
        super().__init__(f"Item '{item_id}' not found.", {"item_id": item_id})


# ── Stats Errors ──────────────────────────────────────────────────

class InsufficientDataError(MetaScopeError):
    """Not enough data to calculate stats (below min_sample_size)."""

    def __init__(self, entity: str, games_available: int, games_required: int) -> None:
        """Initialize with sample size information.

        Args:
            entity: Entity name (champion/item/augment).
            games_available: Number of games currently available.
            games_required: Minimum number of games required.
        """
        super().__init__(
            f"Insufficient data for '{entity}': {games_available} games (requires {games_required}).",
            {
                "entity": entity,
                "games_available": games_available,
                "games_required": games_required,
            },
        )


# ── Cache Errors ──────────────────────────────────────────────────

class CacheError(MetaScopeError):
    """Error when interacting with Redis cache."""

    pass


# ── Validation Errors ─────────────────────────────────────────────

class InvalidPatchError(MetaScopeError):
    """Patch version is invalid or has no data."""

    def __init__(self, patch: str, available_patches: list[str] | None = None) -> None:
        details: dict = {"patch": patch}
        if available_patches:
            details["available_patches"] = available_patches[:5]
        super().__init__(f"Patch '{patch}' not found or has no data.", details)


# ── Auth Errors ──────────────────────────────────────────────────

class UnauthorizedError(MetaScopeError):
    """Authentication required but missing or token is invalid (401)."""

    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__(message)


class ForbiddenError(MetaScopeError):
    """User does not have permission to perform this action (403)."""

    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(message)


class PremiumRequiredError(MetaScopeError):
    """Feature requires a premium tier."""

    def __init__(self, feature: str = "this feature") -> None:
        super().__init__(
            f"Premium subscription required to access {feature}.",
            {"feature": feature, "upgrade_url": "/pricing"},
        )


class RateLimitExceededError(MetaScopeError):
    """App-level rate limit exceeded (distinct from Riot rate limit)."""

    def __init__(self, retry_after: int = 60) -> None:
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after}s.",
            {"retry_after": retry_after},
        )
        self.retry_after = retry_after


class UserBannedError(MetaScopeError):
    """User has been banned."""

    def __init__(self) -> None:
        super().__init__("Your account has been suspended.")


# ── Resource Not Found ───────────────────────────────────────────

class GuideNotFoundError(MetaScopeError):
    """Guide does not exist."""

    def __init__(self, guide_id: str) -> None:
        super().__init__(f"Guide '{guide_id}' not found.", {"guide_id": guide_id})


class CompositionNotFoundError(MetaScopeError):
    """Composition does not exist."""

    def __init__(self, comp_id: str) -> None:
        super().__init__(f"Composition '{comp_id}' not found.", {"comp_id": comp_id})


class AugmentNotFoundError(MetaScopeError):
    """Augment does not exist."""

    def __init__(self, augment_id: str) -> None:
        super().__init__(f"Augment '{augment_id}' not found.", {"augment_id": augment_id})


class TraitNotFoundError(MetaScopeError):
    """Trait does not exist."""

    def __init__(self, trait_name: str) -> None:
        super().__init__(f"Trait '{trait_name}' not found.", {"trait_name": trait_name})


class UserNotFoundError(MetaScopeError):
    """User does not exist."""

    def __init__(self, user_id: str) -> None:
        super().__init__(f"User '{user_id}' not found.", {"user_id": user_id})
