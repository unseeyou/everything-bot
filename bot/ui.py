import re
import typing

import discord
from discord import Message
from discord.components import ActionRow
from discord.ui import Item, View
from discord.ui import view as v


class PersistentView(View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    # noinspection PyProtectedMember
    # O_O YOU SEE NOTHING it's just polymorphism
    # noinspection DuplicatedCode
    @classmethod
    def from_message(cls, message: Message, **kwargs: dict | None) -> "PersistentView":
        # hope and pray this keeps working in future updates
        _component_to_item = v._component_to_item  # noqa: SLF001
        kwargs.clear()  # don't care lol
        view = cls()
        row = 0
        for component in message.components:
            if isinstance(component, ActionRow):
                for child in component.children:
                    item = _component_to_item(child)
                    item.row = row
                    view.add_item(item)
                row += 1
            else:
                item = _component_to_item(component)
                item.row = row
                view.add_item(item)

        return view


class PersistentRoleButton(
    discord.ui.DynamicItem[discord.ui.Button[discord.ui.View]],
    template=r"role_id:(?P<role_id>\d+)",
):
    def __init__(self, role: discord.Role, custom_id: str) -> None:
        super().__init__(discord.ui.Button(style=discord.ButtonStyle.blurple, custom_id=custom_id, label=role.name))
        self.role = role
        self.emoji = role.display_icon

    @classmethod
    async def from_custom_id(
        cls,
        interaction: discord.Interaction,
        item: Item,
        match: re.Match[str],
    ) -> discord.ui.DynamicItem[typing.Any]:
        if isinstance(item, discord.ui.Button):
            return cls(interaction.guild.get_role(int(match.group("role_id"))), match.string)
        return cls(interaction.guild.get_role(int(match.group("role_id"))), match.string)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        if self.role not in interaction.user.roles:
            await interaction.user.add_roles(self.role)
            await interaction.followup.send(
                f"Added {self.role.mention} to {interaction.user.mention}",
                ephemeral=True,
            )
        else:
            await interaction.user.remove_roles(self.role)
            await interaction.followup.send(
                f"Removed {self.role.mention} from {interaction.user.mention}",
                ephemeral=True,
            )
