import uuid
from typing import Literal

from bot.bot import Bot
from bot.economy.economy_objects import EconomyUser, Inventory, ShopItem
from bot.errors import PetNameTooShortError

default_pet = {
    "name": "Unnamed",
    "happy": 50,
    "hunger": 0,
    "id": "unset",
}

dog = ShopItem("Dog", 60, description="Buy a dog to be your pet", emoji="🐶", item_id="pet_dog", data=default_pet)
cat = ShopItem("Cat", 60, description="Buy a cat to be your pet", emoji="🐈", item_id="pet_cat", data=default_pet)


class Pet:
    def __init__(
        self,
        name: str,
        owner_id: int,
        bot: Bot,
        species: Literal["dog", "cat"],
        pet_id: str = "unset",
    ) -> None:  # noqa: PLR0913 RUF100
        self.__happy = 50  # percentage
        self.__hunger = 0  # higher = more hungry
        self.__name = name
        self._user_id = owner_id
        self._bot = bot
        self._type = species
        self.__id = pet_id if pet_id != "unset" else generate_pet_id()

    @property
    def happy(self) -> int:
        return self.__happy

    @property
    def hunger(self) -> int:
        return self.__hunger

    @property
    def name(self) -> str:
        return self.__name

    def to_dict(self) -> dict:
        return {
            "name": self.__name,
            "happy": self.__happy,
            "hunger": self.__hunger,
            "id": self.__id,
        }

    async def update(self) -> None:
        if self._type == "dog":
            dog.data = self.to_dict()
            await self._edit_inventory(dog, "edit")
            dog.data = default_pet
        elif self._type == "cat":
            cat.data = self.to_dict()
            await self._edit_inventory(cat, "edit")
            cat.data = default_pet

    async def _get_user(self) -> EconomyUser:
        balance = await self._bot.database.economy.get_user_bank(self._user_id)
        return EconomyUser(self._user_id, balance[0], balance[1], Inventory.from_string(balance[2]), self._bot)

    async def _edit_inventory(self, item: ShopItem, mode: Literal["edit", "remove"]) -> None:
        user = await self._get_user()
        if mode == "remove":
            await user.inventory_remove_item(item)
        elif mode == "edit":
            for i in user.inventory.items:
                if "id" not in i.data:
                    continue
                if i.data["id"] == item.data["id"]:
                    # prob add an ID to check instead
                    await user.inventory_remove_item(i)
                    await user.inventory_add_item(item)
                    break

    async def feed(self, amount: int) -> None:
        await self.set_hunger(self.__hunger - amount)

    async def set_hunger(self, amount: int) -> None:
        if amount < 0:
            self.__hunger = 0
        else:
            self.__hunger = amount
        await self.update()

    async def set_happy(self, happy: int) -> None:
        if happy > 100:  # noqa: PLR2004
            self.__happy = 100
        elif happy < 0:
            self.__happy = 0
        else:
            self.__happy = happy
        await self.update()

    async def set_name(self, name: str) -> None:
        name_filtered = "".join([letter for letter in name if letter.isalnum()])
        if len(name_filtered) > 1:
            self.__name = "".join([i for i in name if i.isalnum() or i == " "])
        else:
            raise PetNameTooShortError
        await self.update()

    @property
    def type(self) -> str:
        return self._type


def generate_pet_id() -> str:
    return str(uuid.uuid4())
