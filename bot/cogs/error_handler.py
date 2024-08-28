import logging
from contextlib import suppress

from discord import Color, Embed, Interaction, InteractionResponded
from discord.app_commands.errors import (
    AppCommandError,
    BotMissingPermissions,
    CommandInvokeError,
    CommandOnCooldown,
    MissingPermissions,
    NoPrivateMessage,
)
from discord.ext.commands import Cog

from bot.bot import Bot
from bot.errors import DatabaseNotConnectedError, JobDoesNotExistError


class ErrorEmbed(Embed):
    """An embed holding error information.

    Attributes:
        internal: Whether the error is internal (unfixable by the user). This
                  attribute determines whether the report details are shown in
                  the description.
    """

    def __init__(self, error: Exception | str, *, internal: bool = True) -> None:
        super().__init__(
            title="😬 Oops! An error occurred.",
            color=Color.red(),
        )

        self.internal = internal
        self.set_error(error)

    def set_tip(self, tip: str) -> None:
        self.set_footer(text=f"💡 {tip}")

    def set_error(self, error: Exception | str) -> None:
        self.description = f"```\n{type(error)}: {error}\n```" if not isinstance(error, str) else error

        if self.internal:
            # fmt: off
            self.description += "\n-# Please report this issue to unseeyou"
            # fmt: on


class ErrorHandler(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.bot.tree.on_error = self.on_tree_error

    def convert_seconds(self, seconds: float) -> str:
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

    async def create_embed(self, error: Exception | str, embed: ErrorEmbed) -> None:
        if isinstance(error, DatabaseNotConnectedError):
            embed.internal = True
            embed.set_error("Database not connected")

        if isinstance(error, BotMissingPermissions):
            embed.internal = False
            embed.set_error("I don't have the correct permissions to do that.")
            embed.set_tip("Ensure my role is high enough in the role hierarchy.")

        if isinstance(error, MissingPermissions):
            embed.internal = False
            embed.title = "Hey! You don't have the correct permissions to do that."
            embed.set_error(str(error))

        if isinstance(error, NoPrivateMessage):
            embed.internal = False
            embed.set_error("This command can't be used in DMs.")
            embed.set_tip("Use this command in a server.")

        if isinstance(error, CommandOnCooldown):
            embed.internal = False
            embed.set_error("This command is on cooldown.")
            embed.set_tip(f"Try again in {self.convert_seconds(error.retry_after)}")
            embed.title = "Hey! Wait a bit before doing that again."

        if isinstance(error, JobDoesNotExistError):
            logging.disable(logging.NOTSET)
            embed.internal = False
            embed.set_error(
                "This job doesn't exist. Do `/jobs list` to see all available jobs, or pick one from the "
                "autocomplete.",
            )

    async def on_tree_error(
        self,
        interaction: Interaction,
        error: AppCommandError,
    ) -> None:
        with suppress(InteractionResponded):
            await interaction.response.defer()

        embed = ErrorEmbed(error)

        if isinstance(error, CommandInvokeError):
            error = error.original

        await self.create_embed(error, embed)

        await interaction.followup.send(
            embed=embed,
        )

        if embed.internal:
            self.bot.logger.exception(error)


async def setup(bot: Bot) -> None:
    await bot.add_cog(ErrorHandler(bot))
