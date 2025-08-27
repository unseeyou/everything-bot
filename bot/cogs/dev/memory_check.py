import os

import discord
import psutil
from discord.ext import commands

from bot.bot import Bot


class DevEmbed(discord.Embed):
    def __init__(self) -> None:
        super().__init__(color=discord.Color.from_rgb(145, 71, 71))
        self.title = "Current Bot Memory Usage"
        url = "https://implyingrigged.info/w/images/thumb/2/2a/Out_of_date.svg/124px-Out_of_date.svg.png"
        self.set_author(
            name="Current Memory Usage",
            icon_url=url,
        )
        mem_used = self.get_used_memory()
        self.description = f"I currently using `{mem_used:.2f}MB` of memory."

    def get_used_memory(self) -> float:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)


class CheckMemory(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command(name="memory", aliases=["ram", "getram", "getmem", "mem"])
    @commands.is_owner()
    async def _memory(self, ctx: commands.Context) -> None:
        await ctx.send(embed=DevEmbed())


async def setup(bot: Bot) -> None:
    await bot.add_cog(CheckMemory(bot))
