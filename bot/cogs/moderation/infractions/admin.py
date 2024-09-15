import discord
from discord import app_commands
from discord.ext import commands

from bot.bot import Bot


class Admin(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    admin = app_commands.Group(name="admin", description="Admin commands")

    @admin.command(name="warn", description="Warn a user")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(user="The user to warn", reason="The reason for the warning")
    async def warn(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str,
    ) -> None:
        await user.send(
            f"You have been warned in {interaction.guild.name} for {reason}. "
            "Please create a ticket to appeal this action.",
        )
        await interaction.response.send_message(
            f"Warned {user.mention} for {reason}",
        )
        await self.bot.database.infractions.add_infraction(
            guild_id=interaction.guild_id,
            admin_id=interaction.user.id,
            user_id=user.id,
            description=f"Warning |> {reason}",
        )


async def setup(bot: Bot) -> None:
    await bot.add_cog(Admin(bot))
