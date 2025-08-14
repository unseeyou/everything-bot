import logging

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Cog

from bot.bot import Bot
from bot.database.commands import DatabaseIntegrityError


def find_invite_by_code(invite_list: list[discord.Invite], code: str) -> None | discord.Invite:
    for inv in invite_list:
        if inv.code == code:
            return inv
    return None


class LogEmbed(discord.Embed):
    def __init__(self, action: str, author: discord.Member | None = None, comparison: bool = False, **kwargs) -> None:  # noqa: ANN003
        super().__init__(
            title=action,
            color=discord.Color(0x33FFBB),
            timestamp=discord.utils.utcnow(),
        )
        if comparison:
            changes = []
            before: discord.abc.GuildChannel = kwargs.get("before")
            after: discord.abc.GuildChannel = kwargs.get("after")
            if before.name != after.name:
                changes.append(f"**Name:**\n{before.name} -> {after.name}")
            if before.category != after.category:
                changes.append(f"**Category:**\n{before.category} -> {after.category}")
            if before.type != after.type:
                changes.append(f"**Type:**\n{before.type} -> {after.type}")
            if before.overwrites != after.overwrites:
                changes.append(f"**Overwrites:**\n{before.overwrites} -> {after.overwrites}")
            if before.position != after.position:
                changes.append(f"**Position:**\n{before.position} -> {after.position}")
            if before.changed_roles != after.changed_roles:
                changes.append(f"**Role Permissions:**\n{before.changed_roles} -> {after.changed_roles}")
            self.add_field(name="Changes", value="\n".join(changes))

        if author is not None:
            self.set_author(name=f"{author.global_name}({author.display_name})", icon_url=author.display_avatar.url)


class Log(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

        # Role updated (name, permission added/removed)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.bot.logger.info("Loading Guild Invites")
        for guild in self.bot.guilds:
            # Adding each guild's invites to our dict
            self.bot.invites[guild.id] = await guild.invites()
        self.bot.logger.info("Loaded Guild Invites")

    @commands.Cog.listener()
    async def on_guild_role_update(self, role_before: discord.Role, role_after: discord.Role) -> None:
        logchannel_id = await self.bot.database.logs.get_log_channel(role_after.guild.id)
        if logchannel_id is None:
            return
        logchannel = role_after.guild.get_channel(logchannel_id)
        if logchannel is None:
            return
        if role_before.name != role_after.name:  # Check role's name
            embed = discord.Embed(
                title=":pushpin: Role Name Updated",
                color=0x000000,
                timestamp=discord.utils.utcnow(),
                description=role_after.mention,
            )
            embed.set_author(name=role_after.guild.name, icon_url=role_after.guild.icon.url)
            embed.add_field(name="Old:", value=role_before)
            embed.add_field(name="New:", value=role_after)
            embed.set_footer(text=f"{role_after.guild.name}")
            await logchannel.send(embed=embed)
        elif role_before.permissions != role_after.permissions:  # Check role's permissions
            diff = set(role_before.permissions).symmetric_difference(set(role_after.permissions))
            permission = next(iter(diff))[0]
            permission = permission.replace("_", " ").title()
            if next(iter(diff))[1]:
                in_title = "Removed"
                in_des = "removed from"
            else:
                in_title = "Added"
                in_des = "added to"
            embed = discord.Embed(color=0x000000, timestamp=discord.utils.utcnow())
            embed.set_author(name=role_after.guild.name, icon_url=role_after.guild.icon.url)
            embed.add_field(
                name=f":pushpin: Role Permission {in_title}",
                value=f"{permission} {in_des} {role_after.mention}",
            )
            embed.set_footer(text=role_after.guild.name)
            await logchannel.send(embed=embed)

    # Role deleted
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        logchannel_id = await self.bot.database.logs.get_log_channel(role.guild.id)
        if logchannel_id is None:
            return
        logchannel = role.guild.get_channel(logchannel_id)
        if logchannel is None:
            return
        embed = discord.Embed(color=0x000000, timestamp=discord.utils.utcnow())
        embed.set_author(name=role.guild.name, icon_url=role.guild.icon.url)
        embed.add_field(name=":pushpin: Role Deleted", value=role)
        embed.set_footer(text=role.guild.name)
        await logchannel.send(embed=embed)

    # Role created
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        logchannel_id = await self.bot.database.logs.get_log_channel(role.guild.id)
        if logchannel_id is None:
            return
        logchannel = role.guild.get_channel(logchannel_id)
        if logchannel is None:
            return
        embed = discord.Embed(color=0x000000, timestamp=discord.utils.utcnow())
        embed.set_author(name=role.guild.name, icon_url=role.guild.icon.url)
        embed.add_field(name=":pushpin: Role Created", value=role)
        embed.set_footer(text=role.guild.name)
        await logchannel.send(embed=embed)

    # Member unbanned
    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.Member) -> None:
        logchannel_id = await self.bot.database.logs.get_log_channel(guild.id)
        if logchannel_id is None:
            return
        logchannel = guild.get_channel(logchannel_id)
        if logchannel is None:
            return
        embed = discord.Embed(color=0x000000, timestamp=discord.utils.utcnow())
        embed.set_author(name=user.name, icon_url=user.avatar.url)
        embed.add_field(name="⚒️ Member Unbanned", value=user)
        embed.set_thumbnail(url=user.avatar.url)
        embed.set_footer(text=guild.name)
        await logchannel.send(embed=embed)

    # Member banned
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.Member) -> None:
        logchannel_id = await self.bot.database.logs.get_log_channel(guild.id)
        if logchannel_id is None:
            return
        logchannel = guild.get_channel(logchannel_id)
        if logchannel is None:
            return
        embed = discord.Embed(color=0x000000, timestamp=discord.utils.utcnow())
        embed.set_author(name=user.name, icon_url=user.avatar.url)
        embed.add_field(name="⚒️ Member Banned", value=user)
        embed.set_thumbnail(url=user.avatar.url)
        embed.set_footer(text=guild.name)
        await logchannel.send(embed=embed)

    # Member updated (nickname, role, display avatar, timeout)
    @commands.Cog.listener()
    async def on_member_update(self, member_before: discord.Member, member_after: discord.Member) -> None:
        log_channel = await self.bot.database.logs.get_log_channel(member_after.guild.id)
        if member_before.nick != member_after.nick:  # Check member's nickname
            embed = discord.Embed(color=0x000000, timestamp=discord.utils.utcnow())
            embed.set_author(name=member_after.name, icon_url=member_after.avatar.url)
            embed.add_field(name=":house: Member's Nickname Updated", value=member_after)
            embed.add_field(name="**Old Nickname:**", value=member_before.nick)
            embed.add_field(name="**New Nickname:**", value=member_after.nick)
            embed.set_thumbnail(url=member_after.avatar.url)
            embed.set_footer(text=member_after.guild.name)
            channel = self.bot.get_channel(log_channel)
            await channel.send(embed=embed)
        elif member_before.roles != member_after.roles:  # Check member's roles
            diff = (
                str(set(member_before.roles).symmetric_difference(set(member_after.roles)))
                .replace("{", "")
                .replace("}", "")
            )
            diff_id = diff.split("id=")[1].split(" name")[0]
            diff_role = discord.utils.find(lambda r: r.id == int(diff_id), member_after.guild.roles)
            in_des = ""
            if diff_role in member_before.roles:
                in_des = "removed from"
            elif diff_role in member_after.roles:
                in_des = "added to"
            embed = discord.Embed(color=0x000000, timestamp=discord.utils.utcnow())
            embed.set_author(name=member_after.name, icon_url=member_after.avatar.url)
            embed.add_field(
                name=":house: Member's Roles Updated",
                value=f"The role {diff_role.mention} has been {in_des} {member_after.mention}",
            )
            embed.set_thumbnail(url=member_after.avatar.url)
            embed.set_footer(text=member_after.guild.name)
            channel = self.bot.get_channel(log_channel)
            await channel.send(embed=embed)
        elif member_after.is_timed_out():  # Check if member got timeout
            embed = discord.Embed(color=0x000000, timestamp=discord.utils.utcnow())
            embed.set_author(name=member_after.name, icon_url=member_after.avatar.url)
            embed.add_field(name=":house: Member's Timeout", value=f"{member_after.mention} got timeout")
            embed.set_thumbnail(url=member_after.display_avatar.url)
            embed.set_footer(text=member_after.guild.name)
            channel = self.bot.get_channel(log_channel)
            await channel.send(embed=embed)
        elif member_before.display_avatar.url != member_after.display_avatar.url:  # Check member's display avatar
            embed = discord.Embed(color=0x000000, timestamp=discord.utils.utcnow())
            embed.set_author(name=member_after.name, icon_url=member_after.avatar.url)
            embed.add_field(name=":house: Member's Server Avatar Updated", value=member_after)
            embed.set_thumbnail(url=member_after.display_avatar.url)
            embed.set_footer(text=member_after.guild.name)
            channel = self.bot.get_channel(log_channel)
            await channel.send(embed=embed)

    # Message deleted
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        logchannel_id = await self.bot.database.logs.get_log_channel(message.guild.id)
        if logchannel_id is None:
            return
        logchannel = message.guild.get_channel(logchannel_id)
        if logchannel is None:
            return
        deleter = None
        async for entry in message.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):
            if entry.target.channel.id == message.channel.id and entry.target.id == message.author.id:
                deleter = entry.user
                logging.info("Deleter Detected")
            else:
                deleter = message.author
                logging.info("Deleter is self")
        embed = discord.Embed(
            description=f"**Message sent by {message.author.mention} deleted in {message.channel.mention}",
            color=0x000000,
            timestamp=discord.utils.utcnow(),
        )
        embed.description += f" by {deleter.mention}**" if deleter is not None else "**"
        embed.set_author(name=message.author, icon_url=message.author.avatar.url)
        embed.add_field(name="Message:", value=f"{message.content}")
        embed.set_footer(text=message.guild.name)
        await logchannel.send(embed=embed)

    # Message edited
    @commands.Cog.listener()
    async def on_message_edit(self, message_before: discord.Message, message_after: discord.Message) -> None:
        if message_before.content == message_after.content:
            return
        if message_after.author.bot:
            return
        logchannel_id = await self.bot.database.logs.get_log_channel(message_after.guild.id)
        if logchannel_id is None:
            return
        logchannel = message_after.guild.get_channel(logchannel_id)
        if logchannel is None:
            return
        embed = discord.Embed(
            description=f"**Message sent by {message_after.author.mention} edited in {message_after.channel.mention}. "
            f"[Jump to Message]({message_after.jump_url})**",
            color=0x000000,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(name=message_after.author, icon_url=message_after.author.avatar.url)
        embed.add_field(name="Old:", value=f"{message_before.content}")
        embed.add_field(name="New:", value=f"{message_after.content}")
        embed.set_footer(text=message_after.guild.name)
        await logchannel.send(embed=embed)

    # Member joined
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        invites_before_join = self.bot.invites[member.guild.id]
        invites_after_join = await member.guild.invites()
        user_invite = None

        for invite in invites_before_join:
            if invite.uses < find_invite_by_code(invites_after_join, invite.code).uses:
                user_invite: discord.Invite | None = invite
                self.bot.invites[member.guild.id] = invites_after_join
                break

        logchannel_id = await self.bot.database.logs.get_log_channel(member.guild.id)
        if logchannel_id is None:
            return

        logchannel = member.guild.get_channel(logchannel_id)
        if logchannel is None:
            return

        date_format = "%d/%m/%Y %H:%M"
        e = discord.Embed(
            title=f"{member.name} joined!",
            description=f"{member.mention} joined the server.",
            color=0x000000,
            timestamp=discord.utils.utcnow(),
        )

        if user_invite is not None:
            inviter = user_invite.inviter
            invite_url = user_invite.url
            e.description += f"\nInvited by: {inviter.mention} ({invite_url})"

        e.set_author(name=member.name, icon_url=member.avatar.url)
        e.set_thumbnail(url=member.avatar.url)
        e.add_field(name="Age of Account:", value=f"`{member.created_at.strftime(date_format)}`")
        e.set_footer(text=member.guild.name)
        await logchannel.send(embed=e)

    # Member left
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        self.bot.invites[member.guild.id] = await member.guild.invites()
        date_format = "%d/%m/%Y"
        logchannel_id = await self.bot.database.logs.get_log_channel(member.guild.id)
        if logchannel_id is None:
            return
        logchannel = member.guild.get_channel(logchannel_id)
        if logchannel is None:
            return
        e = discord.Embed(
            title=f"{member.name} has left!",
            description=f"{member.mention} left the server.",
            color=0x000000,
            timestamp=discord.utils.utcnow(),
        )
        e.set_author(name=member.name, icon_url=member.avatar.url)
        e.set_thumbnail(url=member.avatar.url)
        e.add_field(name="Age of Account:", value=f"`{member.created_at.strftime(date_format)}`")
        e.add_field(name="Member from:", value=f"`{member.joined_at.strftime(date_format)}`")
        e.set_footer(text=member.guild.name)
        await logchannel.send(embed=e)

    @Cog.listener(name="on_guild_channel_create")
    async def channel_create_log(self, channel: discord.abc.GuildChannel) -> None:
        logchannel_id = await self.bot.database.logs.get_log_channel(channel.guild.id)
        if logchannel_id is None:
            return
        logchannel = channel.guild.get_channel(logchannel_id)
        if logchannel is None:
            return
        embed = LogEmbed(action=f"Created {str(channel.type).title()} Channel `{channel.name}`")
        await logchannel.send(embed=embed)

    @Cog.listener(name="on_guild_channel_delete")
    async def channel_delete_log(self, channel: discord.abc.GuildChannel) -> None:
        logchannel_id = await self.bot.database.logs.get_log_channel(channel.guild.id)
        if logchannel_id is None:
            return
        logchannel = channel.guild.get_channel(logchannel_id)
        if logchannel is None:
            return
        embed = LogEmbed(action=f"Deleted {str(channel.type).title()} Channel `{channel.name}`")
        await logchannel.send(embed=embed)

    @Cog.listener(name="on_guild_channel_update")
    async def channel_update_log(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel) -> None:
        logchannel_id = await self.bot.database.logs.get_log_channel(after.guild.id)
        if logchannel_id is None:
            return
        logchannel = after.guild.get_channel(logchannel_id)
        if logchannel is None:
            return
        embed = LogEmbed(
            action=f"Updated {str(after.type).title()} Channel `{after.name}`",
            comparison=True,
            before=before,
            after=after,
        )
        await logchannel.send(embed=embed)

    # Guild updated (name, icon)
    @commands.Cog.listener()
    async def on_guild_update(self, guild_before: discord.Guild, guild_after: discord.Guild) -> None:
        logchannel_id = await self.bot.database.logs.get_log_channel(guild_after.id)
        if logchannel_id is None:
            return
        logchannel = guild_after.get_channel(logchannel_id)
        if logchannel is None:
            return
        embed = LogEmbed(
            action="Updated Server",
        )
        if guild_before.name != guild_after.name:
            embed.add_field(name="Name", value=f"`{guild_before.name}` -> `{guild_after.name}`")
        if guild_before.icon != guild_after.icon:
            embed.add_field(
                name="Icon",
                value=f"[before]({guild_before.icon.url}) -> [after]({guild_after.icon.url})",
            )
        await logchannel.send(embed=embed)

    # Guild emojis updated
    @commands.Cog.listener()
    async def on_guild_emojis_update(
        self,
        guild: discord.Guild,
        before: list[discord.Emoji],
        after: list[discord.Emoji],
    ) -> None:
        logchannel_id = await self.bot.database.logs.get_log_channel(guild.id)
        if logchannel_id is None:
            return
        logchannel = guild.get_channel(logchannel_id)
        if logchannel is None:
            return
        embed = LogEmbed(
            action="Updated Server Emojis",
        )
        added = [emoji for emoji in after if emoji not in before]
        removed = [emoji for emoji in before if emoji not in after]
        if added:
            embed.add_field(name="Added Emojis", value="\n".join(f"`{emoji.name}`" for emoji in added))
        if removed:
            embed.add_field(name="Removed Emojis", value="\n".join(f"`{emoji.name}`" for emoji in removed))
        await logchannel.send(embed=embed)

    # Guild stickers updated
    @commands.Cog.listener()
    async def on_guild_stickers_update(
        self,
        guild: discord.Guild,
        before: list[discord.Sticker],
        after: list[discord.Sticker],
    ) -> None:
        logchannel_id = await self.bot.database.logs.get_log_channel(guild.id)
        if logchannel_id is None:
            return
        logchannel = guild.get_channel(logchannel_id)
        if logchannel is None:
            return
        embed = LogEmbed(
            action="Updated Server Stickers",
        )
        added = [sticker for sticker in after if sticker not in before]
        removed = [sticker for sticker in before if sticker not in after]
        if added:
            embed.add_field(name="Added Stickers", value="\n".join(f"`{sticker.name}`" for sticker in added))
        if removed:
            embed.add_field(name="Removed Stickers", value="\n".join(f"`{sticker.name}`" for sticker in removed))
        await logchannel.send(embed=embed)

    log = app_commands.Group(
        name="modlog",
        description="Log a message",
        default_permissions=discord.Permissions(permissions=1099511635984),
    )

    @log.command(name="set_channel", description="set the log channel")
    @app_commands.describe(channel="The channel to send the log messages to")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        await self.bot.database.logs.set_log_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message(f"Set log channel to {channel.mention}!")
        logging.info(f"Set log channel of {interaction.guild.id} to {channel.id}")  # noqa: G004

    @log.command(name="unset_channel", description="unset the log channel")
    async def unset_channel(self, interaction: discord.Interaction) -> None:
        await self.bot.database.logs.set_log_channel(interaction.guild.id, None)
        await interaction.response.send_message("Unset log channel!")
        logging.info(f"Unset log channel of {interaction.guild.id}")  # noqa: G004

    @log.command(name="query_channel", description="get the current log channel")
    async def query_channel(self, interaction: discord.Interaction) -> None:
        try:
            channel_id = await self.bot.database.logs.get_log_channel(interaction.guild.id)
            channel = interaction.guild.get_channel(channel_id)
        except DatabaseIntegrityError:
            await interaction.response.send_message(
                "No log channel set! Use `/modlog set_channel` to set a log channel.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(f"The log channel is {channel.mention}", ephemeral=True)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Log(bot))
