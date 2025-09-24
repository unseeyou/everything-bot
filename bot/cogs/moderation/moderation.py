import asyncio
from collections.abc import Sequence

import discord
from discord import app_commands
from discord.ext import commands


class ClearView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=60.0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.manage_channels

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.red, emoji="🛑")
    async def confirm_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        channel = interaction.channel

        await interaction.guild.create_text_channel(
            name=channel.name,
            category=channel.category,
            position=channel.position,
            reason=f"requested by {interaction.user.name} by clicking {button.label} button",
            nsfw=channel.nsfw,
            overwrites=channel.overwrites,
            slowmode_delay=channel.slowmode_delay,
            default_auto_archive_duration=channel.default_auto_archive_duration,
            default_thread_slowmode_delay=channel.default_thread_slowmode_delay,
        )
        await interaction.channel.delete(reason=f"requested by {interaction.user.name}")


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.currently_roll_assigning = []

    moderation = app_commands.Group(
        name="moderation",
        description="Moderation commands",
        default_permissions=discord.Permissions(permissions=1099511635984),
    )

    async def mass_give_roles(
        self,
        members: Sequence[discord.Member],
        role: discord.Role,
        inter: discord.Interaction,
    ) -> None:
        lock = asyncio.Lock()
        async with lock:
            if inter.guild.id in self.currently_roll_assigning:
                await inter.channel.send(
                    "This guild already has a /roleall task running! Please wait before calling this command again.",
                )
                return
            self.currently_roll_assigning.append(inter.guild.id)  # yay fixed the race condition hopefully
        grouped_members = [members[i : i + 10] for i in range(0, len(members), 10)]
        for group in grouped_members:
            for member in group:
                try:
                    await member.add_roles(role)  # this is probably good enough
                except discord.Forbidden:
                    result = f"Error: Missing permissions to update roles for {member.name}"
                    await inter.channel.send(result + f"\n{inter.user.mention}", silent=True)
                except discord.HTTPException as e:
                    result = f"Error: Failed to update roles for {member.name}: {e}"
                    await inter.channel.send(result + f"\n{inter.user.mention}", silent=True)
            await asyncio.sleep(1)
        result = f"Success! {role.mention} added to {len(members)} member(s)."
        await inter.channel.send(result + f"\n{inter.user.mention}", silent=True)
        self.currently_roll_assigning.remove(inter.guild.id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        locked_channels = await self.bot.database.channel_lock.get_locked_channels(message.guild.id)
        if (
            message.channel.id in locked_channels and message.author.id != self.bot.application_id
        ) or message.author.id in locked_channels:
            await message.delete()

    @moderation.command(name="purge", description="Purge x messages from a channel")
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: int,
        reason: str | None = None,
        author: discord.Member | None = None,
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        check = (lambda m: m.author.id == author.id) if author is not None else discord.utils.MISSING
        await interaction.channel.purge(limit=amount, reason=reason, check=check)
        await interaction.edit_original_response(content=f"Deleted {amount} messages")

    @moderation.command(name="clear", description="DANGER!!! This will completely remove everything from a channel")
    async def clear(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await interaction.response.send_message(
            "Wait! Are you sure you want to do this? Everything from this channel will be completely removed!",
            view=ClearView(),
            ephemeral=True,
        )

    @moderation.command(name="lockdown", description="toggle the ability to stop people from speaking in a channel.")
    async def lockdown_toggle(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        locked_channels = await self.bot.database.channel_lock.get_locked_channels(interaction.guild.id)
        if interaction.guild.owner_id != interaction.user.id:
            await interaction.followup.send(":no_entry_sign: Insufficient Permissions: must be server owner")
            return
        if interaction.channel.id in locked_channels:
            await self.bot.database.channel_lock.remove_locked_channel(interaction.channel.id, interaction.guild.id)
            await interaction.followup.send("🔓 Channel Unlocked Successfully!")
        else:
            await self.bot.database.channel_lock.add_locked_channel(interaction.channel.id, interaction.guild.id)
            await interaction.followup.send("🔒 Channel Locked Successfully!")

    @moderation.command(name="silence", description="toggle the ability to silence a server member.")
    async def silence_toggle(self, interaction: discord.Interaction, member: discord.Member) -> None:
        await interaction.response.defer(thinking=True)
        locked_channels = await self.bot.database.channel_lock.get_locked_channels(interaction.guild.id)
        if interaction.guild.owner_id != interaction.user.id:
            await interaction.followup.send(":no_entry_sign: Insufficient Permissions: must be server owner")
            return
        if member.id in locked_channels:
            await self.bot.database.channel_lock.remove_locked_channel(member.id, interaction.guild.id)
            await interaction.followup.send(f"{member.mention}'s voice has been given back.")
        else:
            await self.bot.database.channel_lock.add_locked_channel(member.id, interaction.guild.id)
            await interaction.followup.send(f"🤫 {member.mention} has been silenced.")

    @moderation.command(name="roleall", description="give all members a role")
    @app_commands.default_permissions(manage_roles=True)
    async def _roleall(self, interaction: discord.Interaction, role: discord.Role) -> None:
        await interaction.response.send_message("Assigning roles in the background...")
        await asyncio.create_task(self.mass_give_roles(interaction.guild.members, role, interaction))
        # TODO: probably not best practice to make a task in the command, hopefully will fix soon


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
