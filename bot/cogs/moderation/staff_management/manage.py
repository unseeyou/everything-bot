from typing import Literal

import discord
from discord import Embed, Interaction, app_commands
from discord.ext import commands

from bot.bot import Bot


class NotifyEmbed(Embed):
    def __init__(  # noqa: PLR0913, RUF100
        self,
        member: discord.Member,
        reason: str | None,
        mode: Literal["Strike", "Fire"],
        author: discord.Member,
        guild: discord.Guild,
    ) -> None:
        super().__init__(title="Staff Management Announcement", colour=discord.Colour.og_blurple())
        self.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        if reason is not None:
            self.add_field(name="Reason", value=reason)
        if mode == "Strike":
            self.description = f"A strike has been applied to {member.mention} by {author.mention}"
        elif mode == "Fire":
            self.description = f"{member.mention} was fired by {author.mention}"
        self.set_footer(text=guild.name, icon_url=guild.icon.url)


class StaffManagement(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    staff = app_commands.Group(
        name="staff",
        description="Manage staff members",
        default_permissions=discord.Permissions(permissions=8),
    )

    @staff.command(name="strike", description="Strike a staff member")
    async def strike(
        self,
        interaction: Interaction,
        member: discord.Member,
        reason: str | None = None,
    ) -> None:
        """Strike a staff member"""
        if interaction.user.top_role.position <= member.top_role.position:
            await interaction.response.send_message(
                "You can't strike someone with a higher or equal role than you!",
                ephemeral=True,
            )
            return
        embed = NotifyEmbed(
            member,
            reason,
            "Strike",
            interaction.user,
            interaction.guild,
        )
        await interaction.response.send_message("Done!", ephemeral=True, embed=embed)

        channel = await self.bot.database.logs.get_log_channel(interaction.guild.id)
        if channel is not None:
            await interaction.guild.get_channel(channel).send(embed=embed)
        current_strikes = await self.bot.database.staff.get_user_strikes(member.id)
        await self.bot.database.staff.set_user_strikes(member.id, current_strikes + 1)
        await member.send(embed=embed)

    @staff.command(name="strikes", description="Get the amount of strikes for a staff member")
    async def list_strikes(self, interaction: Interaction, member: discord.Member) -> None:
        """List the strikes for a staff member"""
        strikes = await self.bot.database.staff.get_user_strikes(member.id)
        embed = Embed(
            colour=discord.Colour.blue(),
            description=f"{member.mention} has {strikes} strikes.",
        )
        await interaction.response.send_message(embed=embed)

    @staff.command(name="fire", description="Fire a staff member")
    async def fire(
        self,
        interaction: Interaction,
        member: discord.Member,
        reason: str | None = None,
        role: discord.Role | None = None,
    ) -> None:
        """Fire a staff member"""
        if interaction.user.top_role.position <= member.top_role.position:
            await interaction.response.send_message(
                "You can't fire someone with a higher or equal role than you!",
                ephemeral=True,
            )
            return

        embed = NotifyEmbed(
            member,
            reason,
            "Fire",
            interaction.user,
            interaction.guild,
        )
        await interaction.response.send_message("Done!", ephemeral=True, embed=embed)

        channel = await self.bot.database.logs.get_log_channel(interaction.guild.id)
        if channel is not None:
            await interaction.guild.get_channel(channel).send(embed=embed)
        await self.bot.database.staff.set_user_strikes(member.id, 0)
        await member.send(embed=embed)
        await member.remove_roles(role)

    @staff.command(name="announcement", description="Send a staff announcement")
    async def send_announcement(
        self,
        interaction: Interaction,
        announcement: str,
        channel: discord.TextChannel,
        body: str,
    ) -> None:
        """Send a staff announcement"""
        embed = Embed(
            title=announcement,
            description=body,
            colour=discord.Colour.yellow(),
        )
        url = "https://cdn-icons-png.flaticon.com/512/1378/1378644.png"
        embed.set_author(name="Staff Announcement", icon_url=url)
        embed.set_footer(text=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message("Done! Here is a preview:", ephemeral=True, embed=embed)
        await channel.send(embed=embed)


async def setup(bot: Bot) -> None:
    await bot.add_cog(StaffManagement(bot))
