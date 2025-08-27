import logging

import aiosqlite
import discord
from discord.ext import commands
from rich.logging import RichHandler

from bot import utils
from bot.database.commands import SqliteRepository
from bot.settings import Settings
from bot.ui import PersistentRoleButton


def configure_logging() -> None:
    file_handler = logging.FileHandler("botcmds.log", encoding="utf-8")
    file_formatter = logging.Formatter(
        "%(asctime)s:%(levelname)s:%(name)s: %(message)s",
        "%Y-%m-%d:%H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
        datefmt="%X",
        handlers=[RichHandler(), file_handler],
    )


class Bot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            case_insensitive=True,
            allowed_contexts=discord.app_commands.AppCommandContext(guild=True, dm_channel=False),
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="you all the time",
            ),
        )

        self.settings = Settings()  # pyright: ignore[reportCallIssue]

        self.invites = {}

        configure_logging()
        self.logger = logging.getLogger("botcmds")

        self.database: SqliteRepository | None = None
        self.database_connection: aiosqlite.Connection | None = None

        @self.event
        async def setup_hook() -> None:
            self.logger.info("Syncing commands...")
            cmds = await self.tree.sync(guild=None)
            self.logger.info("Sync complete!")
            self.logger.info(f"Loaded {len(cmds)} commands / command groups!")  # noqa: G004
            self.logger.info("Loading reaction role views")
            self.add_dynamic_items(PersistentRoleButton)
            self.logger.info("Reaction roles loaded")

    async def connect_to_database(self) -> None:
        self.database_connection = await aiosqlite.connect(self.settings.database_path)
        self.database = SqliteRepository(self.database_connection)
        await self.database.initialize()

    async def close_database_connection(self) -> None:
        if self.database_connection is not None:
            await self.database_connection.close()

    async def load_extensions(self, path: str) -> None:
        for file in utils.search_directory(path):
            self.logger.info(f"Loading extension: {file}")  # noqa: G004
            await self.load_extension(file)
