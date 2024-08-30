from discord.app_commands.errors import AppCommandError


class DatabaseNotConnectedError(AppCommandError):
    """Raised when the bot is not connected to the game."""


class JobDoesNotExistError(AppCommandError):
    """Raised when a job does not exist."""


class TooMuchExperienceError(AppCommandError):
    """Raised when the trying to add too much experience to a user that would make them cross the level cap."""


class PetNameTooShortError(AppCommandError):
    """Raised when the pet name is too short."""


class TooManyShopItemsError(AppCommandError):
    """Raised when the shop has too many items."""
