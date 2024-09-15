from bot.economy.economy_objects import Shop
from bot.economy.economy_objects import ShopItem as Item
from bot.economy.pet import cat, dog
from bot.errors import TooManyShopItemsError

# duration = times it gets used, e.g. cookie will boost for 2 work shifts
effects = {
    "2x_pot": {"multiplier": 2, "duration": 8},
    "10x_pot": {"multiplier": 10, "duration": 8},
    "cookie": {"multiplier": 1.2, "duration": 2},
}

pet_food = Item(
    name="Pet food",
    price=50,
    description="Feed your pet some food if it is hungry.",
    emoji="🍴",
)
name_tag = Item(
    "Name Tag",
    100,
    "Give your pet with a name with this name tag.",
    emoji="🏷️",
)
x2_income_pot = Item(
    "2X Income Potion",
    1000,
    "Make more money. (works 8 times)",
    "2x_pot",
    "🍸",
    data=effects["2x_pot"],
)
x10_income_pot = Item(
    "10X Income Potion",
    5000,
    "Make all the money. (works 8 times)",
    item_id="10x_pot",
    emoji="🍷",
    data=effects["10x_pot"],
)
cookie = Item("Cookie", 5, "Yummy.", item_id="cookie", emoji="🍪", data=effects["cookie"])

# MAX 25 ITEMS
bot_shop = Shop(
    name="Shop",
    items=[
        pet_food,
        name_tag,
        dog,
        cat,
        x2_income_pot,
        x10_income_pot,
        cookie,
    ],
)

if len(bot_shop.items) > 25:  # noqa: PLR2004
    raise TooManyShopItemsError
