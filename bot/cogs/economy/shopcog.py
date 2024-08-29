import discord
from discord.ext import commands

from bot.bot import Bot
from bot.economy.economy_objects import EconomyUser, Inventory
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
                name=f"{item.emoji} {item.name}",
                value=f"**Price:** {item.price} 🪙\n*{item.description}*",
            )
        await interaction.response.send_message(embed=embed)

    @shop.command(name="buy", description="buy an item")
    async def buy_item(self, interaction: discord.Interaction, item: str) -> None:
        item = next((i for i in bot_shop.items if i.name == item), None)
        if item is None:
            await interaction.response.send_message("Item not found", ephemeral=True)
            return
        balance = await self.bot.database.economy.get_user_bank(interaction.user.id)
        user = EconomyUser(interaction.user.id, balance[0], balance[1], Inventory.from_string(balance[2]), self.bot)

        if user.wallet_balance < item.price * 100:
            await interaction.response.send_message(
                "You don't have enough money to buy this item", ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"You bought {item.emoji} {item.name} for {item.price} 🪙", ephemeral=True,
        )
        await user.inventory.add_item(item)
        await user.edit_wallet(-item.price * 100)

    @buy_item.autocomplete("item")
    async def item_autocomplete(self, interaction: discord.Interaction, current: str) -> list[discord.app_commands.Choice[str]]:  # noqa: ARG002
        return [discord.app_commands.Choice(name=item.name, value=item.name) for item in bot_shop.items if current.lower() in item.name.lower()]


async def setup(bot: Bot) -> None:
    await bot.add_cog(ShopCog(bot))
