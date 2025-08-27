import random

import discord
from discord.ext import commands

from bot.bot import Bot
from bot.economy.economy_objects import EconomyUser, Inventory

STEAL_CHANCE = 70  # percentage chance of stealing money


class Crime(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    crime = discord.app_commands.Group(name="crime", description="Crime related commands")

    @crime.command(name="steal", description="Steal money from someone's wallet")
    @discord.app_commands.describe(member="The member to rob from")
    @discord.app_commands.checks.cooldown(1, 120 * 60)
    async def steal(self, interaction: discord.Interaction, member: discord.Member) -> None:
        """Steal items from the bank"""

        if interaction.user.id == member.id:
            messages = [
                "Try harder. Maybe one day you'll get extra money from this person.",
                "You can't steal from yourself.",
                "Want more money? Did you work today?",
            ]

            await interaction.response.send_message(
                embed=discord.Embed(
                    description=random.choice(messages),  # noqa: S311
                    colour=discord.Colour.dark_orange(),
                ),
            )
            return

        target_data = await self.bot.database.economy.get_user_bank(member.id)
        target = EconomyUser(
            member.id,
            target_data[0],
            target_data[1],
            Inventory.from_string(target_data[2]),
            self.bot,
        )
        if target.wallet_balance == 0:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{member.mention} is way too poor to steal from. "
                    "They literally have no money in their wallet. You should give them some money if you "
                    "really want to rob from them.",
                    colour=discord.Colour.dark_orange(),
                ),
            )
            return
        user_data = await self.bot.database.economy.get_user_bank(interaction.user.id)
        user = EconomyUser(
            interaction.user.id,
            user_data[0],
            user_data[1],
            Inventory.from_string(user_data[2]),
            self.bot,
        )

        if random.randint(1, 100) > STEAL_CHANCE:  # noqa: S311
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"You stole absolutely nothing from {member.mention}! Wow, you are bad at crime.",
                    colour=discord.Colour.dark_orange(),
                ),
            )
            return

        steal_amount = random.randint(1, min(100, target.wallet_balance)) * 100  # noqa: S311
        await target.edit_wallet(-steal_amount)
        await user.edit_wallet(steal_amount)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"You stole {steal_amount / 100:.2f} :coin: from {member.mention}! "
                f"They now have {target.wallet_balance / 100:.2f} :coin: left in their wallet.",
                colour=discord.Colour.dark_orange(),
            ),
        )

    @crime.command(name="bankrob", description="Rob money from someone's bank")
    @discord.app_commands.describe(member="The member to rob from")
    @discord.app_commands.checks.cooldown(1, 120 * 60)
    async def bankrob(self, interaction: discord.Interaction, member: discord.Member) -> None:
        """Steal items from the bank"""

        if interaction.user.id == member.id:
            messages = [
                "Try harder. Maybe one day you'll get extra money from this person.",
                "You can't steal from yourself.",
                "Want more money? Did you work today?",
            ]

            await interaction.response.send_message(
                embed=discord.Embed(
                    description=random.choice(messages),  # noqa: S311
                    colour=discord.Colour.dark_orange(),
                ),
            )
            return

        target_data = await self.bot.database.economy.get_user_bank(member.id)
        target = EconomyUser(
            member.id,
            target_data[0],
            target_data[1],
            Inventory.from_string(target_data[2]),
            self.bot,
        )
        if target.bank_balance == 0:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{member.mention} is way too poor to steal from. "
                    "They literally have no money in their bank.",
                    colour=discord.Colour.dark_orange(),
                ),
            )
            return
        user_data = await self.bot.database.economy.get_user_bank(interaction.user.id)
        user = EconomyUser(
            interaction.user.id,
            user_data[0],
            user_data[1],
            Inventory.from_string(user_data[2]),
            self.bot,
        )

        if random.randint(1, 100) > STEAL_CHANCE:  # noqa: S311
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"You stole absolutely nothing from {member.mention}! Wow, you are bad at crime.",
                    colour=discord.Colour.dark_orange(),
                ),
            )
            return

        steal_amount = random.randint(1, min(100, target.wallet_balance)) * 100  # noqa: S311
        await target.edit_bank(-steal_amount)
        await user.edit_wallet(steal_amount)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"You stole {steal_amount / 100:.2f} :coin: from {member.mention}! "
                f"They now have {target.wallet_balance / 100:.2f} :coin: left in their bank.",
                colour=discord.Colour.dark_orange(),
            ),
        )


async def setup(bot: Bot) -> None:
    await bot.add_cog(Crime(bot))
