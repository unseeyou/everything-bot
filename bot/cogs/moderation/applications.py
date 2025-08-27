import discord
from discord import Embed, Interaction, app_commands
from discord.app_commands import Choice
from discord.ext import commands

from bot.bot import Bot


class NotifyEmbed(Embed):
    def __init__(self, message: str, notes: str | None = None) -> None:
        super().__init__(color=discord.Color(0xB2FFFA))
        self.title = message
        url = "https://implyingrigged.info/w/images/thumb/2/2a/Out_of_date.svg/124px-Out_of_date.svg.png"
        self.set_author(
            name="Notification",
            icon_url=url,
        )
        if notes is not None:
            self.description = notes


class ApplicationEmbed(Embed):
    def __init__(  # noqa: PLR0913, RUF100
        self,
        success: bool,
        admin: discord.Member,
        target: discord.Member,
        role: str,
        reason: str | None = None,
    ) -> None:
        super().__init__(colour=discord.Colour(0x07C400 if success else 0xC40000))
        self.title = f"{target.display_name}'s `{role.title()}` application was "
        if success:
            self.title += "accepted"
        else:
            self.title += "rejected"
        self.description = f"Applicant: {target.mention}"
        if reason is not None:
            self.description += f"\nReason for {'accepting' if success else 'rejecting'}: {reason}"
        self.add_field(name=f"{'Accepted' if success else 'Rejected'} by", value=admin.mention)
        self.set_author(name=target.display_name, icon_url=target.display_avatar.url)
        self.set_footer(text=admin.display_name, icon_url=admin.display_avatar.url)


class RegisterApplicationModal(discord.ui.Modal):
    def __init__(self, bot: Bot, channel: discord.TextChannel, role: discord.Role) -> None:
        super().__init__(title="Register Application Form")
        self.bot = bot
        self.output_channel = channel
        self.role = role

    name = discord.ui.TextInput(label="Name", placeholder="Name of the role that is being applied for")
    questions = discord.ui.TextInput(
        label="Questions",
        placeholder="1. How old are you?\n2. etc\n(QUESTIONS WILL BE SPLIT BY LINE, MAX 5 QUESTIONS)",
        max_length=1200,
        style=discord.TextStyle.paragraph,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        questions = self.questions.value.split("\n")
        await self.bot.database.applications.add_application_role(
            role_name=self.name.value,
            questions=questions,
            guild_id=interaction.guild_id,
            channel=self.output_channel.id,
            role_id=self.role.id,
        )
        await interaction.response.send_message(f"Added {self.name.value}!", ephemeral=True)


class ApplicationModal(discord.ui.Modal):
    def __init__(self, bot: Bot, questions: list[str], role: str) -> None:
        super().__init__(title=f"{role.title()} Application Form")
        self.bot = bot
        self.role = role
        self.questions = questions
        for question in self.questions:
            self.add_item(discord.ui.TextInput(label=question, placeholder="Your answer here", min_length=1))

    async def on_submit(self, interaction: Interaction) -> None:
        application = await self.bot.database.applications.get_application(self.role, interaction.guild_id)
        answers = [child.value for child in self.children]
        output_channel = interaction.guild.get_channel(application[1])
        if output_channel is None:
            return
        accept = "</applications accept:1273807157317337161>"
        deny = "</applications deny:1273807157317337161>"
        embed = discord.Embed(
            title=f"{self.role.title()} Application • {interaction.user.display_name}",
            description=f"{accept} or {deny} to accept or decline this application",
            color=discord.Colour.brand_green(),
        )
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        for question in self.questions:
            embed.add_field(name=question, value=answers[self.questions.index(question)], inline=False)
        await self.bot.database.applications.add_application_user(
            username=interaction.user.name,
            guild_id=interaction.guild_id,
            role_name=self.role,
            role_id=application[2],
        )
        await output_channel.send(embed=embed)
        await interaction.response.send_message("Your application has been submitted!", ephemeral=True)


class Applications(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    applications = app_commands.Group(name="applications", description="Applications related commands")

    @applications.command(name="add", description="Add an application form")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(output_channel="The channel to send the application form to", role="The role to apply for")
    async def add_app(
        self,
        interaction: discord.Interaction,
        output_channel: discord.TextChannel,
        role: discord.Role,
    ) -> None:
        await interaction.response.send_modal(
            RegisterApplicationModal(bot=self.bot, channel=output_channel, role=role),
        )

    @applications.command(name="remove", description="Remove an application form")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(application_name="The name of the application form")
    async def remove_app(self, interaction: discord.Interaction, application_name: str) -> None:
        """Remove an application form"""
        await self.bot.database.applications.remove_application_role(application_name, interaction.guild_id)
        await interaction.response.send_message(f"Removed {application_name}!", ephemeral=True)

    @applications.command(name="apply", description="Apply for a role on the server")
    @app_commands.describe(role="The role to apply for")
    async def apply(self, interaction: discord.Interaction, role: str) -> None:
        """Apply for a role on the server"""
        questions = await self.bot.database.applications.get_application(role, interaction.guild_id)
        await interaction.response.send_modal(ApplicationModal(bot=self.bot, questions=questions[0], role=role))

    @applications.command(name="accept", description="Accept an application")
    @app_commands.describe(application_name="The name of the application form")
    async def accept(self, interaction: discord.Interaction, application_name: str, member: discord.Member) -> None:
        """Accept an application"""
        role_id = await self.bot.database.applications.get_application_role(
            username=member.name,
            guild_id=interaction.guild_id,
            role_name=application_name,
        )

        if role_id is None:
            await interaction.response.send_message(
                f"{member.display_name} doesn't have an application for {application_name}!",
                ephemeral=True,
            )
            return

        role = interaction.guild.get_role(role_id[0])
        await member.add_roles(role)

        await interaction.response.send_message(
            f"Accepted {member.display_name}'s application!\nGave them {role.mention} role!",
            ephemeral=True,
        )
        await member.send(
            embed=NotifyEmbed(
                f"Congratulations! You have been accepted for {application_name} in {interaction.guild.name}!",
                notes=f"You have received: `{role.name}` role",
            ),
        )

        output_channel_id = await self.bot.database.applications.get_application_channel(
            role_name=f"{application_name}:{interaction.guild_id}",
        )

        channel = interaction.guild.get_channel(output_channel_id[0])
        await channel.send(
            embed=ApplicationEmbed(
                success=True,
                admin=interaction.user,
                target=member,
                role=application_name,
            ),
        )

        await self.bot.database.applications.remove_application_user(
            username=member.name,
            guild_id=interaction.guild_id,
            app_name=application_name,
        )

    @applications.command(name="deny", description="Deny an application")
    @app_commands.describe(application_name="The name of the application form")
    async def deny(
        self,
        interaction: discord.Interaction,
        application_name: str,
        member: discord.Member,
        reason: str | None = None,
    ) -> None:
        """Deny an application"""
        if reason is None:
            reason = "No reason supplied"
        remove = await self.bot.database.applications.remove_application_user(
            username=member.name,
            guild_id=interaction.guild_id,
            app_name=application_name,
        )
        if not remove:
            await interaction.response.send_message(
                "This user has no such application!",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True)
        await member.send(
            embed=NotifyEmbed(
                f"Your application for {application_name} has been denied by {interaction.user.name}!",
                notes=f"Reason: `{reason}`",
            ),
        )
        await interaction.followup.send(f"Denied {member.display_name}'s application!", ephemeral=True)

        output_channel_id = await self.bot.database.applications.get_application_channel(
            role_name=f"{application_name}:{interaction.guild_id}",
        )

        channel = interaction.guild.get_channel(output_channel_id[0])
        await channel.send(
            embed=ApplicationEmbed(
                success=False,
                admin=interaction.user,
                target=member,
                role=application_name,
                reason=reason,
            ),
        )

    @apply.autocomplete("role")
    @deny.autocomplete("application_name")
    @remove_app.autocomplete("application_name")
    @accept.autocomplete("application_name")
    async def autocomplete_role(self, interaction: discord.Interaction, current: str) -> list[Choice[str]]:
        roles = await self.bot.database.applications.get_application_roles(interaction.guild_id)
        return [
            app_commands.Choice(name="".join(role[0].split(":")[0]), value="".join(role[0].split(":")[0]))
            for role in roles
            if current.lower() in "".join(role[0].split(":")[0]).lower()
        ]


async def setup(bot: Bot) -> None:
    await bot.add_cog(Applications(bot))
