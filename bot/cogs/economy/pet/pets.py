from random import randint

import discord
from discord import app_commands
from discord.ext import commands

from bot.bot import Bot
from bot.economy.economy_objects import EconomyUser, Inventory, ShopItem
from bot.economy.pet import Pet
from bot.economy.shop import name_tag, pet_food

PLAY_HUNGER_LIMIT = 12


class PetEmbed(discord.Embed):
    def __init__(self, message: str, pet: Pet | None) -> None:
        if pet is not None:
            super().__init__(
                description=f"{"🐕" if pet.type == "dog" else "🐈"} {message}",
                colour=discord.Colour.dark_orange(),
            )
        else:
            super().__init__(description=message, colour=discord.Colour.dark_orange())


class PetCommands(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def create_pet(self, item: ShopItem, user_id: int) -> Pet:
        pet = Pet(item.data["name"], user_id, self.bot, "dog" if item.item_id == "pet_dog" else "cat", item.data["id"])
        await pet.set_hunger(item.data["hunger"])
        await pet.set_happy(item.data["happy"])
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
            if item.item_id.startswith("pet") and item.data["id"] == pet:
                return await self.create_pet(item, interaction.user.id)
        await interaction.response.send_message("You don't have a pet! Buy one from the shop.")
        return None

    pets = app_commands.Group(name="pets", description="Pet related commands")

    @pets.command(name="list", description="view your pets")
    async def view_pets(self, interaction: discord.Interaction) -> None:
        user = await self.get_user(interaction.user.id)
        pets = []
        for item in user.inventory.items:
            if item.item_id.startswith("pet"):
                pet = await self.create_pet(item, interaction.user.id)
                pets.append(pet)

        embed = discord.Embed(
            title=f"{interaction.user.name}'s Pets",
            colour=discord.Colour.from_rgb(141, 111, 100),
        )
        for pet in pets:
            embed.add_field(
                name=f"{'🐕' if pet.type == 'dog' else '🐈'} {pet.name}",
                value=f"**Hunger Level:** {pet.hunger}\n**Happiness:** {pet.happy}%",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    @pets.command(name="set", description="select a pet to interact with")
    async def select_pet(self, interaction: discord.Interaction, pet: str) -> None:
        await self.bot.database.pets.set_current_pet(interaction.user.id, pet)
        pet = await self.get_pet(interaction)
        await interaction.response.send_message(f"Your current pet has been set to {pet.name}!", ephemeral=True)

    @select_pet.autocomplete("pet")
    async def select_pet_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice]:
        user = await self.get_user(interaction.user.id)
        return [
            app_commands.Choice(name=f"{item.emoji} {item.data['name']}", value=item.data["id"])
            for item in user.inventory.items
            if item.item_id.startswith("pet") and item.data["name"].startswith(current)
        ]

    @pets.command(name="name", description="change your pet's name")
    async def change_pet_name(self, interaction: discord.Interaction, name: str) -> None:
        old = await self.bot.database.pets.get_current_pet(interaction.user.id)
        if old == "None":
            await interaction.response.send_message(
                embed=PetEmbed("You don't have a pet selected currently! `/pets set` one.", None),
            )
            return
        user = await self.get_user(interaction.user.id)
        if len([i for i in user.inventory.items if i.name == "Name Tag"]) == 0:
            await interaction.response.send_message(
                embed=PetEmbed("🏷️ You don't have a name tag! Buy one from the shop.", None),
            )
            return
        await user.inventory_remove_item(name_tag)
        for item in user.inventory.items:
            if item.item_id.startswith("pet") and item.data["id"] == old:
                pet = await self.create_pet(item, interaction.user.id)
                await pet.set_name(name)
                await interaction.response.send_message(
                    embed=PetEmbed(
                        f"Your pet's name has been set to {name}!",
                        None,
                    ),
                )
                return

        await interaction.response.send_message(
            embed=PetEmbed("You don't have a pet! Buy one from the shop.", None),
        )

    @pets.command(name="feed", description="feed your pet")
    async def feed_pet(self, interaction: discord.Interaction) -> None:
        pet = await self.get_pet(interaction)
        if pet is None:
            return
        if pet.hunger < 1:
            await interaction.response.send_message(embed=PetEmbed("Your pet is already full!", pet))
            return
        user = await self.get_user(interaction.user.id)
        if len([i for i in user.inventory.items if i.name == "Pet Food"]) == 0:
            await interaction.response.send_message(
                embed=PetEmbed("You don't have any pet food! Buy one from the shop.", pet),
            )
            return
        await user.inventory_remove_item(pet_food)
        feed_amount = randint(1, min(5, pet.hunger))  # noqa: S311
        await pet.feed(feed_amount)
        await interaction.response.send_message(embed=PetEmbed(f"You fed your pet {feed_amount} treats!", pet))

    @pets.command(name="play", description="play with your pet")
    async def play_pet(self, interaction: discord.Interaction) -> None:
        pet = await self.get_pet(interaction)
        if pet is None:
            return
        if pet.hunger > PLAY_HUNGER_LIMIT:
            await interaction.response.send_message(f"{pet.name} is too hungry to play.")
            return
        gained_joy = randint(0, 100 - pet.happy)  # noqa: S311
        hunger_consumed = randint(0, min(PLAY_HUNGER_LIMIT, pet.hunger))  # noqa: S311
        await pet.set_happy(pet.happy + gained_joy)
        await pet.set_hunger(pet.hunger - hunger_consumed)
        await interaction.response.send_message(
            embed=PetEmbed(
                f"You played with your pet and it gained {gained_joy}% happiness!\nIt is now {pet.happy}% happy!",
                pet,
            ),
        )

    @pets.command(name="view", description="view your pet")
    async def view_pet(self, interaction: discord.Interaction) -> None:
        pet = await self.get_pet(interaction)
        if pet is None:
            return
        embed = discord.Embed(
            title=f"{interaction.user.name}'s Pet",
            colour=discord.Colour.from_rgb(141, 111, 100),
            description=f"**Name:** {pet.name}\n**Hunger:** {pet.hunger}\n**Happiness:** {pet.happy}%",
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: Bot) -> None:
    await bot.add_cog(PetCommands(bot))
