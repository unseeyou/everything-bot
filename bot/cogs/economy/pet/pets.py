from discord.ext import commands

from bot.bot import Bot


class PetCommands(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot


async def setup(bot: Bot) -> None:
    await bot.add_cog(PetCommands(bot))
