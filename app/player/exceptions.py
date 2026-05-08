"""Player-specific exceptions."""

from app.core.exceptions import MetaScopeError


class PlayerNotFoundError(MetaScopeError):
    """Player does not exist."""

    def __init__(self, game_name: str, tag_line: str) -> None:
        super().__init__(
            f"Player '{game_name}#{tag_line}' not found.",
            {"game_name": game_name, "tag_line": tag_line},
        )
