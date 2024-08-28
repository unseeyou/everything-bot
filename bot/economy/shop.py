from bot.economy.economy_objects import Shop
from bot.economy.economy_objects import ShopItem as Item

bot_shop = Shop(name="Shop", items=[
    Item(name="Pet food", price=5, description="Feed your pet some food if it is hungry."),
    Item("Name Tag", 10, "Give your pet with a name with this name tag."),
    Item("Dog", 60, description="Buy a dog to be your pet"),
    Item("Cat", 60, description="Buy a cat to be your pet"),
    Item("Mystery Potion", 15, "I wonder what these do?"),
    Item("2X Income Potion", 100, "Double your income for a day with this potion."),
    Item("10X Income Potion", 500, "Make all the money. (lasts 3 hours)"),
    Item("Cookie", 5, "Yummy."),
])
