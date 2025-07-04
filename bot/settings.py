from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for the bot.

    This is a subclass of `pydantic_settings.BaseSettings` that loads settings
    in the environment variables starting with `ZZ_`. For example, the field
    `discord_bot_token` will be read from `ZZ_DISCORD_BOT_TOKEN`.

    Leave the prefix blank to load all environment variables (not recommended).

    Alongside reading from the environment variables passed in, it also loads
    them from a `.env` file if it exists.

    Attributes:
        discord_bot_token: The Discord bot token taken from the developer portal.
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="UNS_")

    discord_bot_token: str
    database_path: str = "game.db"
    twitch_client_id: str
    twitch_secret: str
