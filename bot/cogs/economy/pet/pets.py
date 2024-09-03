import discord
from discord import app_commands
from discord.ext import commands

from bot.bot import Bot
from bot.economy.economy_objects import EconomyUser, Inventory
from bot.economy.pet import Pet


class PetCommands(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    pets = app_commands.Group(name="pets", description="Pet related commands")

    @pets.command(name="view", description="view your pets")
    async def view_pets(self, interaction: discord.Interaction) -> None:
        balance = await self.bot.database.economy.get_user_bank(interaction.user.id)
        user = EconomyUser(interaction.user.id, balance[0], balance[1], Inventory.from_string(balance[2]), self.bot)
        pets = []
        for item in user.inventory.items:
            if item.item_id.startswith("pet"):
                pet = Pet(item.data["name"])
                pet.set_hunger(item.data["hunger"])
                pet.set_happy(item.data["happy"])
                pets.append(pet)

        embed = discord.Embed(
            title=f"{interaction.user.name}'s Pets",
            colour=discord.Colour.from_rgb(141, 111, 100),
        )
        for pet in pets:
            embed.add_field(
                name=f"{pet.emoji} {pet.name}",
                value=f"**Hunger Level:** {pet.hunger}\n**Happiness:** {pet.happy}%",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    @pets.command(name="set", description="select a pet to interact with")
    async def select_pet(self, interaction: discord.Interaction, pet: str) -> None:
        await self.bot.database.pets.set_current_pet(interaction.user.id, pet)
        await interaction.response.send_message(f"Your pet has been set to {pet}!")

    @pets.command(name="name", description="change your pet's name")
    async def change_pet_name(self, interaction: discord.Interaction, name: str) -> None:
        old = await self.bot.database.pets.get_current_pet(interaction.user.id)
        await self.bot.database.pets.set_current_pet(interaction.user.id, name)
        balance = await self.bot.database.economy.get_user_bank(interaction.user.id)
        user = EconomyUser(interaction.user.id, balance[0], balance[1], Inventory.from_string(balance[2]), self.bot)

        for item in user.inventory.items:
            if item.item_id.startswith("pet") and item.data["name"] == old:
                item.data["name"] = name
                break
        await interaction.response.send_message(f"Your pet's name has been set to {name}!")



async def setup(bot: Bot) -> None:
    await bot.add_cog(PetCommands(bot))
