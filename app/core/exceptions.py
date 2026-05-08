"""Custom exception hierarchy cho MetaScope API.

Tất cả exceptions của app đều kế thừa từ MetaScopeError.
Route handlers bắt exceptions này và trả HTTP response phù hợp.
"""


class MetaScopeError(Exception):
    """Base exception cho toàn bộ ứng dụng."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        """Khởi tạo exception với message và details tuỳ chọn.

        Args:
            message: Human-readable error message.
            details: Dict chứa thêm context, sẽ được include trong response.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ── Riot API Errors ───────────────────────────────────────────────

class RiotAPIError(MetaScopeError):
    """Lỗi khi gọi Riot Games API."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retry_after: int | None = None,
    ) -> None:
        """Khởi tạo RiotAPIError.

        Args:
            message: Mô tả lỗi.
            status_code: HTTP status code từ Riot API nếu có.
            retry_after: Số giây cần chờ trước khi retry (cho 429).
        """
        super().__init__(message, {"status_code": status_code})
        self.status_code = status_code
        self.retry_after = retry_after


class RiotRateLimitError(RiotAPIError):
    """Riot API rate limit exceeded (429)."""

    def __init__(self, retry_after: int = 1) -> None:
        """Khởi tạo với retry_after header value.

        Args:
            retry_after: Số giây phải chờ, từ Retry-After header.
        """
        super().__init__(
            f"Riot API rate limit exceeded. Retry after {retry_after}s.",
            status_code=429,
            retry_after=retry_after,
        )


class RiotAPIKeyInvalidError(RiotAPIError):
    """Riot API key không hợp lệ hoặc hết hạn (403)."""

    def __init__(self) -> None:
        super().__init__(
            "Riot API key is invalid or expired. Please renew at developer.riotgames.com.",
            status_code=403,
        )


# ── Player Errors ─────────────────────────────────────────────────

class PlayerNotFoundError(MetaScopeError):
    """Player không tồn tại trong hệ thống Riot."""

    def __init__(self, game_name: str, tag_line: str) -> None:
        """Khởi tạo với Riot ID.

        Args:
            game_name: Tên game của player.
            tag_line: Tag của player.
        """
        super().__init__(
            f"Player '{game_name}#{tag_line}' not found.",
            {"game_name": game_name, "tag_line": tag_line},
        )


# ── Match Errors ──────────────────────────────────────────────────

class MatchNotFoundError(MetaScopeError):
    """Match ID không tồn tại trong DB."""

    def __init__(self, match_id: str) -> None:
        """Khởi tạo với match ID.

        Args:
            match_id: Riot match ID, ví dụ VN2_123456789.
        """
        super().__init__(
            f"Match '{match_id}' not found.",
            {"match_id": match_id},
        )


# ── Champion / Item Errors ────────────────────────────────────────

class ChampionNotFoundError(MetaScopeError):
    """Champion ID không tồn tại trong DB."""

    def __init__(self, champion_id: str, suggestions: list[str] | None = None) -> None:
        """Khởi tạo với champion ID và suggestions từ fuzzy search.

        Args:
            champion_id: Champion unit ID hoặc tên.
            suggestions: Danh sách tên gợi ý nếu có.
        """
        details: dict = {"champion_id": champion_id}
        if suggestions:
            details["suggestions"] = suggestions
        super().__init__(
            f"Champion '{champion_id}' not found.",
            details,
        )


class ItemNotFoundError(MetaScopeError):
    """Item ID không tồn tại trong DB."""

    def __init__(self, item_id: str) -> None:
        super().__init__(f"Item '{item_id}' not found.", {"item_id": item_id})


# ── Stats Errors ──────────────────────────────────────────────────

class InsufficientDataError(MetaScopeError):
    """Không đủ dữ liệu để tính stats (dưới min_sample_size)."""

    def __init__(self, entity: str, games_available: int, games_required: int) -> None:
        """Khởi tạo với thông tin sample size.

        Args:
            entity: Tên entity (champion/item/augment).
            games_available: Số game hiện có.
            games_required: Số game tối thiểu yêu cầu.
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
    """Lỗi khi thao tác với Redis cache."""

    pass


# ── Validation Errors ─────────────────────────────────────────────

class InvalidPatchError(MetaScopeError):
    """Patch version không hợp lệ hoặc không có dữ liệu."""

    def __init__(self, patch: str, available_patches: list[str] | None = None) -> None:
        details: dict = {"patch": patch}
        if available_patches:
            details["available_patches"] = available_patches[:5]
        super().__init__(f"Patch '{patch}' not found or has no data.", details)


# ── Auth Errors ──────────────────────────────────────────────────

class UnauthorizedError(MetaScopeError):
    """Yêu cầu authentication nhưng không có hoặc token không hợp lệ (401)."""

    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__(message)


class ForbiddenError(MetaScopeError):
    """User không có quyền thực hiện action này (403)."""

    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(message)


class PremiumRequiredError(MetaScopeError):
    """Tính năng yêu cầu premium tier."""

    def __init__(self, feature: str = "this feature") -> None:
        super().__init__(
            f"Premium subscription required to access {feature}.",
            {"feature": feature, "upgrade_url": "/pricing"},
        )


class RateLimitExceededError(MetaScopeError):
    """App-level rate limit exceeded (khác với Riot rate limit)."""

    def __init__(self, retry_after: int = 60) -> None:
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after}s.",
            {"retry_after": retry_after},
        )
        self.retry_after = retry_after


class UserBannedError(MetaScopeError):
    """User đã bị ban."""

    def __init__(self) -> None:
        super().__init__("Your account has been suspended.")


# ── Resource Not Found ───────────────────────────────────────────

class GuideNotFoundError(MetaScopeError):
    """Guide không tồn tại."""

    def __init__(self, guide_id: str) -> None:
        super().__init__(f"Guide '{guide_id}' not found.", {"guide_id": guide_id})


class CompositionNotFoundError(MetaScopeError):
    """Composition không tồn tại."""

    def __init__(self, comp_id: str) -> None:
        super().__init__(f"Composition '{comp_id}' not found.", {"comp_id": comp_id})


class AugmentNotFoundError(MetaScopeError):
    """Augment không tồn tại."""

    def __init__(self, augment_id: str) -> None:
        super().__init__(f"Augment '{augment_id}' not found.", {"augment_id": augment_id})


class TraitNotFoundError(MetaScopeError):
    """Trait không tồn tại."""

    def __init__(self, trait_name: str) -> None:
        super().__init__(f"Trait '{trait_name}' not found.", {"trait_name": trait_name})


class UserNotFoundError(MetaScopeError):
    """User không tồn tại."""

    def __init__(self, user_id: str) -> None:
        super().__init__(f"User '{user_id}' not found.", {"user_id": user_id})
