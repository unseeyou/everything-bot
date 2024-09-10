import random
from ast import literal_eval
from contextlib import suppress

from discord.ext.commands import Bot


class Job:
    def __init__(self, name: str, description: str, salary: int) -> None:
        self.__name = name
        self.__description = description
        self.__salary = salary * 100

    @property
    def name(self) -> str:
        return self.__name

    @property
    def description(self) -> str:
        return self.__description

    @property
    def salary(self) -> float:
        return self.__salary / 100

    def set_description(self, description: str) -> str:
        if not description:
            msg = "Description cannot be empty"
            raise ValueError(msg)
        self.__description = description
        return self.description

    def set_name(self, name: str) -> str:
        if not name:
            msg = "Name cannot be empty"
            raise ValueError(msg)
        self.__name = name
        return self.name

    def set_salary(self, salary: int) -> float:
        if salary <= 0:
            msg = "Salary must be greater than 0"
            raise ValueError(msg)
        self.__salary = salary * 100
        return self.salary


class ShopItem:
    def __init__(  # noqa: PLR0913
        self,
        name: str,
        price: int,
        description: str,
        item_id: str = "",
        emoji: str = "",
        data: dict | None = None,
    ) -> None:  # noqa: PLR0913, RUF100
        if data is None:
            data = {}
        self.__name = name
        self.__price = price
        self.__description = description
        self.__id = item_id
        self.emoji = emoji
        self.data = data

    def __str__(self) -> str:
        return f"('{self.name}', {self.price}, '{self.description}', '{self.item_id}', '{self.emoji}', {self.data})"

    @property
    def item_id(self) -> str:
        return self.__id

    @property
    def price(self) -> int:
        return self.__price

    @property
    def name(self) -> str:
        return self.__name

    @property
    def description(self) -> str:
        return self.__description

    def set_price(self, price: int) -> int:
        if price <= 0:
            msg = "Price must be greater than 0"
            raise ValueError(msg)
        self.__price = price
        return self.__price

    def set_description(self, description: str) -> str:
        if not description:
            msg = "Description cannot be empty"
            raise ValueError(msg)
        self.__description = description
        return self.description

    def set_name(self, name: str) -> str:
        if not name:
            msg = "Name cannot be empty"
            raise ValueError(msg)
        self.__name = name
        return self.name


class Shop:
    def __init__(self, name: str, items: list[ShopItem]) -> None:
        self.__name = name
        self.__items = items

    @property
    def name(self) -> str:
        return self.__name

    @property
    def items(self) -> list[ShopItem]:
        return self.__items

    def add_item(self, item: ShopItem) -> None:
        self.__items.append(item)

    def remove_item(self, item: ShopItem) -> None:
        with suppress(ValueError):
            self.__items.remove(item)


class Inventory:
    def __init__(self, items: list[ShopItem]) -> None:
        self.__items = items

    def __str__(self) -> str:
        return str([str(i) for i in self.__items])

    @classmethod
    def from_string(cls, string: str) -> "Inventory":
        items = []
        for item in literal_eval(string):
            data = literal_eval(item)
            items.append(ShopItem(data[0], data[1], data[2], data[3], data[4], data[5]))
        return cls(items)

    @property
    def items(self) -> list[ShopItem]:
        return self.__items

    def add_item(self, item: ShopItem) -> None:
        self.__items.append(item)

    def remove_item(self, item: ShopItem) -> None:
        if item.item_id.startswith("pet"):
            for i in self.__items:
                if i.data == {}:
                    continue
                if i.data["id"] == item.data["id"]:
                    self.__items.remove(i)
                    break
            return
        for i in self.__items:
            if i.name == item.name:
                self.__items.remove(i)
                break


class EconomyUser:
    def __init__(  # noqa: PLR0913
        self,
        user_id: int,
        wallet_balance: int,
        bank_balance: int,
        inventory: Inventory,
        bot: Bot,
        job: Job = None,
    ) -> None:
        self.__user_id = user_id
        self.__total_balance = wallet_balance + bank_balance
        self.__inventory = inventory
        self.__wallet_balance = wallet_balance
        self.__bank_balance = bank_balance
        self.__bot = bot
        self.__job = job

    async def __update(self) -> None:
        if self.__job is None:
            self.__job = await self.__bot.database.economy.get_job(self.__user_id)
        await self.__bot.database.economy.set_user_bank(
            self.__user_id,
            self.__wallet_balance,
            self.__bank_balance,
            str(self.__inventory),
        )

    @property
    def total_balance(self) -> int:
        return self.__total_balance

    @property
    def user_id(self) -> int:
        return self.__user_id

    @property
    def inventory(self) -> Inventory:
        return self.__inventory

    @property
    def wallet_balance(self) -> int:
        return self.__wallet_balance

    @property
    def bank_balance(self) -> int:
        return self.__bank_balance

    async def edit_wallet(self, amount: int) -> int:
        self.__wallet_balance += amount
        self.__total_balance += amount
        await self.__update()
        return self.__wallet_balance

    async def edit_bank(self, amount: int) -> int:
        self.__bank_balance += amount
        self.__total_balance += amount
        await self.__update()
        return self.__bank_balance

    async def inventory_add_item(self, item: ShopItem) -> Inventory:
        self.__inventory.add_item(item)
        await self.__update()
        return self.inventory

    async def inventory_remove_item(self, item: ShopItem) -> Inventory:
        self.__inventory.remove_item(item)
        await self.__update()
        return self.inventory

    async def unhappy_pets(self) -> None:
        """Call this in the work command so pets slowly lose happiness when the user is working"""
        for item in self.inventory.items:
            if item.item_id.startswith("pet"):
                item.data["happy"] -= random.randint(5, 15)  # noqa: S311
                item.data["happy"] = max(item.data["happy"], 0)
        await self.__update()

    async def multiply_earnings(self, amount: int) -> int:
        for item in self.inventory.items:
            if "potion" in item.item_id or "cookie" in item.item_id:
                amount *= item.data["multiplier"]
        await self.__update()
        return int(amount)
