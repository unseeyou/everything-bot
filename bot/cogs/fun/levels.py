from random import randint

import discord
from discord import Embed, Interaction, Member, app_commands
from discord.ext import commands

from bot.bot import Bot
from bot.levels.images.generate import create_level_icon
from bot.levels.level_system import LEVEL_CAP, LevelUser


class LevelEmbed(Embed):
    def __init__(self, user: LevelUser) -> None:
        super().__init__(color=discord.Color.blue())
        self.user = user
        self.add_field(name="Level", value=str(user.level), inline=False)
        self.add_field(name="Total XP", value=str(user.xp), inline=False)
        self.file = create_level_icon(user.level, user.user_id)
        self.set_thumbnail(url=f"attachment://level_icon_{user.user_id}.png")

    def set_title(self, title: str) -> None:
        self.title = title

    async def set_ranking(self) -> None:
        self.add_field(name="Rank", value=str(await self.user.get_ranking()).replace("-1", "Unranked"), inline=False)
        self.add_field(name="XP to next level", value=str(await self.user.exp_required()), inline=False)


class LevelUpEmbed(Embed):
    def __init__(self, user: LevelUser, username: str) -> None:
        username = username.replace("{", "").replace("}", "")  # prevent shenanigans
        super().__init__(
            color=discord.Color.from_rgb(153, 255, 255),
            title=f"🎉 Congrats on the rankup, {username}! You are now level {user.level}.",
        )
        self.user = user
        self.file = create_level_icon(user.level, user.user_id)
        self.set_author(icon_url=f"attachment://level_icon_{user.user_id}.png", name="UnseebotV3")


class Levels(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    levels = app_commands.Group(name="levels", description="Level related commands")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None:  # ignore DM channel
            return
        if message.author.bot:
            return
        user = await LevelUser.from_db(message.author.id, message.guild.id, self.bot)
        lvl_old = user.level
        await user.add_xp(randint(15, 25))  # noqa: S311
        if user.level > lvl_old:
            await message.reply(embed=LevelUpEmbed(user=user, username=message.author.display_name))

    @levels.command(name="level", description="View your or someone else's level info")
    @app_commands.describe(member="The member to view the level info of")
    async def level(self, interaction: Interaction, member: Member = None) -> None:
        if not member:
            member = interaction.user
        user = await LevelUser.from_db(member.id, member.guild.id, self.bot)
        embed = LevelEmbed(user)
        await embed.set_ranking()
        embed.set_author(icon_url=member.display_avatar.url, name=member.name)
        await interaction.response.send_message(embed=embed, file=embed.file)

    @levels.command(name="set_level", description="set someone's level")
    @app_commands.describe(member="The member to set the level of", level="The level to set")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def set_level(self, interaction: Interaction, member: Member, level: int) -> None:
        if not member:
            member = interaction.user
        if member.bot:
            await interaction.response.send_message(
                embed=Embed(
                    title="You can't set the level of bots!",
                    colour=discord.Colour.red(),
                ),
            )
            return
        if level > LEVEL_CAP:
            level = LEVEL_CAP
        elif level < 0:
            level = 1
        user = await LevelUser.from_db(member.id, member.guild.id, self.bot)
        await user.set_xp(user.requirements[level - 1])
        embed = LevelEmbed(user)
        await embed.set_ranking()
        embed.set_author(icon_url=member.display_avatar.url, name=member.name)
        await interaction.response.send_message(embed=embed, file=embed.file)

    @levels.command(name="leaderboard", description="View the level leaderboard")
    async def leaderboard(self, interaction: Interaction) -> None:
        members = [i for i in interaction.guild.members if not i.bot]
        member_levels = []
        for member in members:
            user = await LevelUser.from_db(member.id, member.guild.id, self.bot)
            member_levels.append((member, user))
        member_levels.sort(key=lambda x: x[1].xp, reverse=True)
        embed = discord.Embed(title="🏆  LEADERBOARD - TOP 10 USERS", color=discord.Color.blue())
        for i, m in enumerate(member_levels[:10]):
            embed.add_field(
                name=f"#{i + 1} - {m[0].display_name}",
                value=f"Level: {m[1].level}\nXP: {m[1].xp:,}",
                inline=False,
            )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7107/7107530.png")
        await interaction.response.send_message(embed=embed)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Levels(bot))
