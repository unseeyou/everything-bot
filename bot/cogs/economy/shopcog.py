import discord
from discord.ext import commands

from bot.bot import Bot
from bot.economy.shop import bot_shop


class ShopCog(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    shop = discord.app_commands.Group(name="shop", description="Shop related commands")

    @shop.command(name="view", description="view the shop")
    async def view_shop(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(title="Item Shop", colour=discord.Colour.from_rgb(141, 111, 100))
        for item in bot_shop.items:
            embed.add_field(
                name=f"{item.name} {item.emoji}",
                value=f"**Price:** {item.price} 🪙\n*{item.description}*",
            )
        await interaction.response.send_message(embed=embed)


async def setup(bot: Bot) -> None:
    await bot.add_cog(ShopCog(bot))
