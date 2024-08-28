from bot.economy.economy_objects import Shop
from bot.economy.economy_objects import ShopItem as Item

bot_shop = Shop(name="Shop", items=[
    Item(name="Pet food", price=5, description="Feed your pet some food if it is hungry."),
    Item("Name Tag", 10, "Give your pet with a name with this name tag."),
    Item("Dog", 60, description="Buy a dog to be your pet"),
    Item("Cat", 60, description="Buy a cat to be your pet"),
])
