from random import randint

import discord
from discord import app_commands
from discord.ext import commands

from bot.bot import Bot
from bot.economy.economy_objects import EconomyUser, Inventory, ShopItem
from bot.economy.pet import Pet
from bot.economy.shop import name_tag, pet_food

PLAY_HUNGER_LIMIT = 12


class PetCommands(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    def create_pet(self, item: ShopItem) -> Pet:
        pet = Pet(item.data["name"])
        pet.set_hunger(item.data["hunger"])
        pet.set_happy(item.data["happy"])
        return pet

    async def get_user(self, user_id: int) -> EconomyUser:
        balance = await self.bot.database.economy.get_user_bank(user_id)
        return EconomyUser(user_id, balance[0], balance[1], Inventory.from_string(balance[2]), self.bot)

    async def get_pet(self, interaction: discord.Interaction) -> Pet | None:
        pet = await self.bot.database.pets.get_current_pet(interaction.user.id)
        if pet == "None":
            await interaction.response.send_message("You don't have a pet selected currently! `/pets set` one.")
            return None
        user = await self.get_user(interaction.user.id)
        for item in user.inventory.items:
            if item.item_id.startswith("pet") and item.data["name"] == pet:
                return self.create_pet(item)
        await interaction.response.send_message("You don't have a pet! Buy one from the shop.")
        return None

    pets = app_commands.Group(name="pets", description="Pet related commands")

    @pets.command(name="list", description="view your pets")
    async def view_pets(self, interaction: discord.Interaction) -> None:
        user = await self.get_user(interaction.user.id)
        pets = []
        for item in user.inventory.items:
            if item.item_id.startswith("pet"):
                pet = self.create_pet(item)
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
        if old == "None":
            await interaction.response.send_message("You don't have a pet selected currently! `/pets set` one.")
            return
        await self.bot.database.pets.set_current_pet(interaction.user.id, name)
        user = await self.get_user(interaction.user.id)
        if len([i for i in user.inventory.items if i.name == "Name Tag"]) == 0:
            await interaction.response.send_message("You don't have a name tag! Buy one from the shop.")
            return
        user.inventory.remove_item(name_tag)
        for item in user.inventory.items:
            if item.item_id.startswith("pet") and item.data["name"] == old:
                item.data["name"] = name
                await interaction.response.send_message(f"Your pet's name has been set to {name}!")
                return
        await interaction.response.send_message("You don't have a pet! Buy one from the shop.")

    @pets.command(name="feed", description="feed your pet")
    async def feed_pet(self, interaction: discord.Interaction) -> None:
        pet = await self.get_pet(interaction)
        if pet.hunger < 1:
            await interaction.response.send_message("Your pet is already full!")
            return
        user = await self.get_user(interaction.user.id)
        if len([i for i in user.inventory.items if i.name == "Pet Food"]) == 0:
            await interaction.response.send_message("You don't have any pet food! Buy one from the shop.")
            return
        user.inventory.remove_item(pet_food)
        feed_amount = randint(1, min(5, pet.hunger))  # noqa: S311
        pet.feed(feed_amount)
        await interaction.response.send_message(f"You fed your pet {feed_amount} treats!")

    @pets.command(name="play", description="play with your pet")
    async def play_pet(self, interaction: discord.Interaction) -> None:
        pet = await self.get_pet(interaction)
        if pet.hunger > PLAY_HUNGER_LIMIT:
            await interaction.response.send_message(f"{pet.name} is too hungry to play.")
            return
        gained_joy = randint(0, 100-pet.happy)  # noqa: S311
        pet.set_happy(pet.happy + gained_joy)
        await interaction.response.send_message(f"You played with your pet and it gained {gained_joy}% happiness!"
                                                "\nIt is now {pet.happy}% happy!")

    @pets.command(name="view", description="view your pet")
    async def view_pet(self, interaction: discord.Interaction) -> None:
        pet = await self.get_pet(interaction)
        embed = discord.Embed(
            title=f"{interaction.user.name}'s Pet",
            colour=discord.Colour.from_rgb(141, 111, 100),
            description=f"**Name:** {pet.name}\n**Hunger:** {pet.hunger}\n**Happiness:** {pet.happy}%",
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: Bot) -> None:
    await bot.add_cog(PetCommands(bot))
