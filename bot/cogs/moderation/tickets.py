import discord
from discord import app_commands
from discord.ext import commands

from bot.bot import Bot


class NotifyEmbed(discord.Embed):
    def __init__(self, message: str, notes: str | None = None) -> None:
        super().__init__(color=discord.Color.dark_blue())
        self.title = message
        url = "https://implyingrigged.info/w/images/thumb/2/2a/Out_of_date.svg/124px-Out_of_date.svg.png"
        self.set_author(
            name="Notification",
            icon_url=url,
        )
        if notes is not None:
            self.description = notes


class Tickets(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener(name="on_member_remove")
    async def unload_server_config(self, member: discord.Member) -> None:
        if member.id == self.bot.user.id:
            guild = member.guild
            await self.bot.database.tickets.remove_ticket_data(guild.id)

    tickets = app_commands.Group(name="tickets", description="Ticket related commands")
    ticket_config = app_commands.Group(name="config", description="Ticket config commands", parent=tickets)

    @tickets.command(name="create", description="create a new ticket")
    async def create_ticket(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            category_id = await self.bot.database.tickets.get_ticket_category(interaction.guild_id)
        except TypeError:
            await interaction.followup.send("Ticket Category has not been configured for this server.")
            return
        category = await interaction.guild.fetch_channel(category_id)
        for channel in category.text_channels:
            if channel.name.startswith(interaction.user.name):
                await interaction.followup.send(f"You already have a ticket open! -> {channel.mention}")
                return
        num = await self.bot.database.tickets.get_ticket_count(interaction.guild_id)
        channel = await category.create_text_channel(f"{interaction.user.name}-{num}")
        await interaction.followup.send(f"Ticket created at {channel.mention}")
        admin_ids = await self.bot.database.tickets.get_ticket_admins(interaction.guild_id)
        pings = [f"<@&{admin_id}>" for admin_id in admin_ids]
        await channel.send(f"Ticket created by {interaction.user.mention}")
        ping = await channel.send(f"Alerting Staff: {', '.join(pings) if pings else 'None'}")
        await ping.delete(delay=2)
        await self.bot.database.tickets.add_guild_ticket_count(interaction.guild_id)

    @tickets.command(name="close", description="close a ticket")
    @app_commands.checks.has_permissions(administrator=True)
    async def close_ticket(self, interaction: discord.Interaction, reason: str) -> None:
        try:
            if interaction.channel.category_id != await self.bot.database.tickets.get_ticket_category(
                interaction.guild_id,
            ):
                await interaction.response.send_message("This is not a ticket channel!", ephemeral=True)
                return
        except TypeError:
            await interaction.response.send_message("This is not a ticket channel!", ephemeral=True)
            return
        username = interaction.channel.name.split("-")[0]
        member = interaction.guild.get_member_named(username)
        if not interaction.user.guild_permissions.administrator or interaction.user.name != username:
            await interaction.response.send_message(
                "You can only close your own ticket! (Unless you are an admin)",
                ephemeral=True,
            )
            return
        await interaction.channel.delete(reason="Ticket closed")
        if member is not None:
            await member.send(
                embed=NotifyEmbed(
                    f"Your ticket has been closed by {interaction.user.name}",
                    notes=f"Ticket: {interaction.channel.name}\nReason: {reason}",
                ),
            )

    @ticket_config.command(name="set_category", description="set the ticket config for this guild")
    @app_commands.checks.has_permissions(administrator=True)
    async def category_ticket(self, interaction: discord.Interaction, category: discord.CategoryChannel) -> None:
        await self.bot.database.tickets.add_guild_ticket_data(
            guild_id=interaction.guild_id,
            category_id=category.id,
        )
        await interaction.response.send_message(f"Ticket category set to {category.mention}", ephemeral=True)

    @ticket_config.command(
        name="add_staff",
        description="add a role to the ticket config that gets pinged when a new ticket opens",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def add_staff(self, interaction: discord.Interaction, role: discord.Role) -> None:
        await self.bot.database.tickets.add_ticket_admin(
            guild_id=interaction.guild_id,
            admin_id=role.id,
        )
        await interaction.response.send_message(f"Added {role.mention} to ticket staff", ephemeral=True)

    @ticket_config.command(name="list_staff", description="list all current ticket staff roles")
    async def list_staff(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        roles = await self.bot.database.tickets.get_ticket_admins(interaction.guild_id)
        embed = discord.Embed(
            title="Ticket Staff Roles",
            description="** • **" + ("\n** • **".join(guild.get_role(role).mention for role in roles)),
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @ticket_config.command(
        name="remove_staff",
        description="remove a role from the ticket config that gets pinged when a new ticket opens",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_staff(self, interaction: discord.Interaction, role: discord.Role) -> None:
        try:
            await self.bot.database.tickets.remove_ticket_admin(guild_id=interaction.guild_id, admin_id=role.id)
        except ValueError:
            await interaction.response.send_message(
                f"{role.mention} is not currently a ticket support staff role",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(f"Removed {role.mention} from ticket staff", ephemeral=True)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Tickets(bot))
