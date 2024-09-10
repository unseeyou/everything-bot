import logging

import discord
from discord.ext import commands

from bot.bot import Bot
from bot.economy.economy_objects import EconomyUser, Inventory
from bot.economy.jobs import get_job_from_str, jobs, unemployed
from bot.errors import JobDoesNotExistError


class JobCommands(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    jobs = discord.app_commands.Group(name="job", description="Job related commands")

    @jobs.command(name="list")
    async def list_jobs(self, interaction: discord.Interaction) -> None:
        """List all jobs"""
        embed = discord.Embed(
            title="Jobs",
            colour=discord.Colour.og_blurple(),
        )
        for job in jobs:
            embed.add_field(
                name=f"{job.name}",
                value=f"({job.salary:.2f} :coin: per shift)\n{job.description}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed)

    @jobs.command(name="apply")
    async def apply(self, interaction: discord.Interaction, job: str) -> None:
        """Apply for a job"""

        if await self.bot.database.economy.get_job(interaction.user.id) not in (None, unemployed):
            embed = discord.Embed(
                colour=discord.Colour.og_blurple(),
                title="You already have a job!",
                description="You can resign from your current job with `/job resign`",
            )
            await interaction.response.send_message(embed=embed)
            return

        job = get_job_from_str(job)
        if job is None:
            logging.disable()
            raise JobDoesNotExistError

        await self.bot.database.economy.set_job(interaction.user.id, job)
        embed = discord.Embed(
            colour=discord.Colour.og_blurple(),
            title=f"You now work as a {job.name.lower()}!",
        )
        await interaction.response.send_message(embed=embed)

    @apply.autocomplete("job")
    async def apply_job_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[discord.app_commands.Choice[str]]:
        if interaction.user.id is None:  # not sure if this would ever happen but just to be safe
            return []
        if not current:
            return [discord.app_commands.Choice(name=job.name, value=job.name) for job in jobs]
        return [
            discord.app_commands.Choice(name=job.name, value=job.name)
            for job in jobs
            if current.lower() in job.name.lower()
        ]

    @jobs.command(name="work")
    @discord.app_commands.checks.cooldown(1, 15 * 60)  # 15 min cooldown
    async def work(self, interaction: discord.Interaction) -> None:
        """Work at a job"""
        bank = await self.bot.database.economy.get_user_bank(interaction.user.id)
        user = EconomyUser(interaction.user.id, bank[0], bank[1], Inventory.from_string(bank[2]), self.bot)
        job = await self.bot.database.economy.get_job(interaction.user.id)
        if job is None or job == unemployed:
            embed = discord.Embed(
                colour=discord.Colour.og_blurple(),
                title="You don't have a job! Apply for one with `/job apply`!",
            )
            await interaction.response.send_message(embed=embed)
            return
        await user.edit_wallet(int(job.salary * 100))
        embed = discord.Embed(
            colour=discord.Colour.og_blurple(),
            title=f"You earned {job.salary:.2f} :coin: for working as a {job.name.lower()}!",
        ).set_footer(text="You can work a shift again in 15 minutes")
        await user.unhappy_pets()
        await interaction.response.send_message(embed=embed)

    @jobs.command(name="current", description="Shows you your current job")
    async def show_job(self, interaction: discord.Interaction) -> None:
        """Show your current job"""
        job = await self.bot.database.economy.get_job(interaction.user.id)
        if job is None or job == unemployed:
            embed = discord.Embed(
                colour=discord.Colour.og_blurple(),
                title="You don't have a job! Apply for one with `/job apply`!",
            )
        else:
            embed = discord.Embed(
                colour=discord.Colour.og_blurple(),
                title=f"You are currently working as a {job.name.lower()}!",
            )
        await interaction.response.send_message(embed=embed)

    @jobs.command(name="resign", description="Resign from your current job")
    async def resign(self, interaction: discord.Interaction) -> None:
        """Resign from your current job"""
        await self.bot.database.economy.set_job(interaction.user.id, unemployed)
        embed = discord.Embed(
            colour=discord.Colour.og_blurple(),
            title="You have resigned from your current job!",
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: Bot) -> None:
    await bot.add_cog(JobCommands(bot))
