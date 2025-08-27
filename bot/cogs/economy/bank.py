import asyncio
import datetime

import discord
from discord.ext import commands, tasks

from bot.bot import Bot
from bot.economy.economy_objects import EconomyUser, Inventory


class ErrorEmbed(discord.Embed):
    def __init__(self, msg: str) -> None:
        super().__init__(
            title=f"❌ {msg}",
            color=discord.Colour.red(),
        )


class Bank(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.update_bank.start()

    def cog_unload(self) -> None:
        self.update_bank.cancel()

    @tasks.loop(time=datetime.time(hour=8))  # 6PM AEST in UTC is 8 AM
    async def update_bank(self) -> None:
        await self.bot.database.economy.do_bank_interest()

    @update_bank.before_loop
    async def before_update_bank(self) -> None:
        while not self.bot.is_ready():
            await asyncio.sleep(1)

    bank = discord.app_commands.Group(name="bank", description="Bank related commands")

    @bank.command(name="balance", description="Check the current balance of someone's bank and wallet")
    async def balance(self, interaction: discord.Interaction, member: discord.Member = None) -> None:
        if member is None:
            member = interaction.user
        balance = await self.bot.database.economy.get_user_bank(member.id)
        user = EconomyUser(interaction.user.id, balance[0], balance[1], Inventory.from_string(balance[2]), self.bot)
        embed = discord.Embed(
            title=f"{member.display_name}'s balance",
            description=f"**Wallet**: {user.wallet_balance / 100:.2f} :coin:"
            f"\n**Bank**: {user.bank_balance / 100:.2f} :coin:",
            color=discord.Colour.og_blurple(),
        )
        await interaction.response.send_message(embed=embed)

    @bank.command(name="deposit", description="Deposit money into your bank from your wallet")
    async def deposit(self, interaction: discord.Interaction, amount: float) -> None:
        amount *= 100
        amount = int(round(amount, 0))
        if amount <= 0:
            await interaction.response.send_message(embed=ErrorEmbed("You can't deposit less than 0.01 :coin:!"))
            return
        balance = await self.bot.database.economy.get_user_bank(interaction.user.id)
        user = EconomyUser(interaction.user.id, balance[0], balance[1], Inventory.from_string(balance[2]), self.bot)
        if amount > user.wallet_balance:
            await interaction.response.send_message(embed=ErrorEmbed("Insufficient funds in your wallet!"))
            return
        await user.edit_bank(amount)
        await user.edit_wallet(-amount)
        await interaction.response.send_message(f"Deposited {amount / 100} :coin: into your bank!")

    @bank.command(name="withdraw", description="Withdraw money from your bank into your wallet")
    async def withdraw(self, interaction: discord.Interaction, amount: float) -> None:
        amount *= 100
        amount = int(round(amount, 0))
        if amount <= 0:
            await interaction.response.send_message(embed=ErrorEmbed("You can't withdraw less than 0.01 :coin:!"))
            return
        balance = await self.bot.database.economy.get_user_bank(interaction.user.id)
        user = EconomyUser(interaction.user.id, balance[0], balance[1], Inventory.from_string(balance[2]), self.bot)
        if amount > user.bank_balance:
            await interaction.response.send_message(embed=ErrorEmbed("Insufficient funds in your bank!"))
            return
        await user.edit_bank(-amount)
        await user.edit_wallet(amount)
        await interaction.response.send_message(f"Withdrew {amount / 100} :coin: from your bank!")

    @bank.command(name="transfer", description="Transfer money from your wallet to someone else")
    async def transfer(self, interaction: discord.Interaction, member: discord.Member, amount: float) -> None:
        if member.id == interaction.user.id:
            await interaction.response.send_message(embed=ErrorEmbed("You can't transfer money to yourself silly!"))
            return
        amount *= 100
        amount = int(round(amount, 0))
        if amount <= 0:
            await interaction.response.send_message(embed=ErrorEmbed("You can't transfer less than 0.01 :coin:!"))
            return
        balance = await self.bot.database.economy.get_user_bank(interaction.user.id)
        user = EconomyUser(interaction.user.id, balance[0], balance[1], Inventory.from_string(balance[2]), self.bot)
        if amount > user.wallet_balance:
            await interaction.response.send_message(embed=ErrorEmbed("Insufficient funds in your wallet!"))
            return
        await user.edit_wallet(-amount)
        updated_balance = await self.bot.database.economy.get_user_bank(member.id)
        target = EconomyUser(
            member.id,
            updated_balance[0],
            updated_balance[1],
            Inventory.from_string(updated_balance[2]),
            self.bot,
        )
        await target.edit_wallet(amount)
        await interaction.response.send_message(
            f"Transferred {amount / 100} :coin: from your wallet to {member.mention}!",
        )


async def setup(bot: Bot) -> None:
    await bot.add_cog(Bank(bot))
