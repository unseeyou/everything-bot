import discord
from discord import app_commands
from discord.ext import commands

from bot.bot import Bot
from bot.ui import PersistentRoleButton, PersistentView


class ReactionRoles(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    reaction_roles = app_commands.Group(
        name="reaction_roles",
        description="Reaction roles related commands",
        default_permissions=discord.Permissions(permissions=1099511635984),
    )

    @reaction_roles.command(name="add", description="Add a reaction role message")
    async def add_reaction_role(  # noqa: PLR0913
        self,
        interaction: discord.Interaction,
        message_content: str,
        role1: discord.Role,
        role2: discord.Role = None,
        role3: discord.Role = None,
        role4: discord.Role = None,
        role5: discord.Role = None,
    ) -> None:
        await interaction.response.send_message("sending message", ephemeral=True)
        roles = [role1, role2, role3, role4, role5]
        roles = [role for role in roles if role is not None]
        view = PersistentView()
        for role in roles:
            button = PersistentRoleButton(
                role=role,
                custom_id=f"role_id:{role.id}",
            )
            view.add_item(button)
        await interaction.channel.send(message_content, view=view)


async def setup(bot: Bot) -> None:
    await bot.add_cog(ReactionRoles(bot))
