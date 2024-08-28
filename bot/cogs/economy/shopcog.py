import discord
from discord.ext import commands

from bot.bot import Bot
from bot.economy.economy_objects import Shop, ShopItem, EconomyUser


class ShopCog(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    shop = discord.app_commands.Group(name="shop", description="Shop related commands")

    @shop.command(name="view", description="view the shop")
    async def view_shop(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("not implemented")


async def setup(bot: Bot) -> None:
    await bot.add_cog(ShopCog(bot))
