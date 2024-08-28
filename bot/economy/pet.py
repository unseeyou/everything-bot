import random

from bot.errors import PetNameTooShortError


class Pet:
    def __init__(self, name: str = "Unnamed") -> None:
        self.__happy = 50  # percentage
        self.__hunger = 0  # higher = more hungry
        self.__name = name

    @property
    def happy(self) -> int:
        return self.__happy

    @property
    def hunger(self) -> int:
        return self.__hunger

    @property
    def name(self) -> str:
        return self.__name

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

    def set_name(self, name: str) -> None:
        if len(name) > 1:
            self.__name = name
        else:
            raise PetNameTooShortError
