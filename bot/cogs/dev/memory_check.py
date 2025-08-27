import os

import discord
import psutil
from discord.ext import commands

from bot.bot import Bot


class DevEmbed(discord.Embed):
    def __init__(self, previous: float) -> None:
        super().__init__(color=discord.Color.from_rgb(145, 71, 71))
        self.title = "Current Bot Memory Usage"
        url = "https://upload.wikimedia.org/wikipedia/commons/5/55/Magnifying_glass_icon.svg"
        self.set_author(name="Memory Usage Lookup", icon_url=url)
        self.mem_used = self.get_used_memory()
        self.description = f"I currently using `{self.mem_used:.2f} MB` of memory."
        self.set_footer(text=f"Previous Check: {previous:.2f} MB")

    def get_used_memory(self) -> float:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)


class CheckMemory(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.previous_usage = -1.0

    @commands.command(name="memory", aliases=["ram", "getram", "getmem", "mem"])
    @commands.is_owner()
    async def _memory(self, ctx: commands.Context) -> None:
        embed = DevEmbed(self.previous_usage)
        self.previous_usage = embed.mem_used
        await ctx.send(embed=embed)


async def setup(bot: Bot) -> None:
    await bot.add_cog(CheckMemory(bot))
