class GameError(Exception):
    """An expected failure whose message is safe to show the player.

    The global error handler shows these as a red embed. Anything that is not a
    GameError is treated as a bug: logged with a traceback, generic reply.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NoNation(GameError):
    def __init__(self) -> None:
        super().__init__("You don't have a nation yet. Create one with `/createnation`.")


class NotEnough(GameError):
    """The player can't afford something."""


class OnCooldown(GameError):
    """An action was used again before its cooldown ended."""


class WrongAge(GameError):
    """The item isn't available in the player's current age."""
