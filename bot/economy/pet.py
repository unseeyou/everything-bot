import random

from markdown_it.common.html_re import attribute

from bot.economy.economy_objects import ShopItem


class Pet(ShopItem):
    def __init__(self, name: str, price: int, description: str) -> None:
        super().__init__(name, price, description)
        self.__happy = 50  # percentage
        self.__hunger = 0  # higher = more hungry

    @property
    def happy(self) -> int:
        return self.__happy

    @property
    def hunger(self) -> int:
        return self.__hunger

    def play(self) -> None:
        self.__happy += random.randint(1, 5)  # noqa: S311

    def feed(self, amount: int) -> None:
        self.set_hunger(amount)

    def set_hunger(self, amount: int) -> None:
        value = self.hunger - amount
        if value < 0:
            self.__hunger = 0
        else:
            self.__hunger = value

    def set_happy(self, happy: int) -> None:
        if happy > 100:  # noqa: PLR2004
            self.__happy = 100
        elif happy < 0:
            self.__happy = 0
        else:
            self.__happy = happy
