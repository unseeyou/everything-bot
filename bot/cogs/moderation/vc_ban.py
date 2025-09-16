import discord
from discord import app_commands
from discord.ext import commands

from bot.bot import Bot


class VcManagement(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.banned_users: list[int] = []

    @commands.Cog.listener(name="on_voice_state_update")
    async def disconnect_banned_users(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.id in self.banned_users and after.channel:
            await member.move_to(None, reason="automated action requested by admin")
        elif before.channel is not None:
            pass

    vc_mod = app_commands.Group(name="vcmod", description="Voice Channel Management related commands")

    @vc_mod.command(name="ban", description="stop a user from joining a vc")
    async def ban(self, interaction: discord.Interaction, user: discord.Member) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        if interaction.user.id == interaction.guild.owner_id:
            self.banned_users.append(user.id)
            await interaction.followup.send(f"banned {user.mention} from joining voice channels.")
        else:
            await interaction.followup.send("Insufficient Permissions: must be guild owner.")

    @vc_mod.command(name="unban", description="vc unban a user")
    @app_commands.checks.has_permissions(administrator=True)
    async def unban(self, interaction: discord.Interaction, user: discord.Member) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        if interaction.user.id == interaction.guild.owner_id:
            self.banned_users.remove(user.id)
            await interaction.followup.send(f"unbanned {user.mention} from joining voice channels.")
        else:
            await interaction.followup.send("Insufficient Permissions: must be guild owner.")


async def setup(bot: Bot) -> None:
    await bot.add_cog(VcManagement(bot))
