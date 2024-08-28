from bot.economy.economy_objects import Shop
from bot.economy.economy_objects import ShopItem as Item

bot_shop = Shop(name="Shop", items=[
    Item(name="Pet food", price=5, description="Feed your pet some food if it is hungry."),
    Item("Name Tag", 10, "Give your pet with a name with this name tag."),
    Item("Dog", 60, description="Buy a dog to be your pet"),
    Item("Cat", 60, description="Buy a cat to be your pet"),
    Item("Mystery Potion", 15, "I wonder what these do?"),
    Item("2X Income Potion", 100, "Make more money. (works 8 times)", "2x_pot"),
    Item("10X Income Potion", 500, "Make all the money. (works 8 times)", item_id="10x_pot"),
    Item("Cookie", 5, "Yummy.", item_id="cookie"),
])

# duration in hours
effects = {
    "2x_pot": {"multiplier": 2, "duration": 8},
    "10x_pot": {"multiplier": 10, "duration": 8},
    "cookie": {"multiplier": 1.2, "duration": 2},
}
