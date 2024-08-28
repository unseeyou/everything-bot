from bot.bot import Bot

LEVEL_CAP = 100


class LevelUser:
    def __init__(self, user_id: int, xp: int, guild_id: int, bot: Bot) -> None:
        self.__user_id = user_id
        self.__guild_id = guild_id
        self.__xp = xp
        self.__xp_requirements = [0]
        self.__db_table = f"levels_{guild_id}"  # DO NOT EDIT THIS
        diff = 100
        for n in range(LEVEL_CAP + 1):  # adjust the range as needed
            self.__xp_requirements.append(self.__xp_requirements[-1] + diff)
            diff += 55 + 10 * n
        self.__xp_requirements.pop(0)
        self.__bot = bot

    @classmethod
    async def from_db(cls, user_id: int, guild_id: int, bot: Bot) -> "LevelUser":
        xp = await bot.database.levels.get_levels_user(user_id, guild_id)
        return cls(user_id, xp, guild_id, bot)

    @property
    def user_id(self) -> int:
        return self.__user_id

    @property
    def guild_id(self) -> int:
        return self.__guild_id

    @property
    def xp(self) -> int:
        return self.__xp

    @property
    def level(self) -> int:
        for lvl in range(LEVEL_CAP + 1):
            if self.__xp < self.__xp_requirements[lvl]:
                return lvl
        return -1

    @property
    def requirements(self) -> list[int]:
        return self.__xp_requirements

    async def add_xp(self, amount: int) -> int:
        self.__xp += amount
        await self.__bot.database.levels.add_levels_xp(amount, self.user_id, self.__db_table)
        return self.__xp

    async def remove_xp(self, amount: int) -> int:
        self.__xp -= amount
        await self.__bot.database.levels.add_levels_xp(-amount, self.user_id, self.__db_table)
        return self.__xp

    async def set_xp(self, amount: int) -> int:
        self.__xp = amount
        await self.__bot.database.levels.set_levels_xp(amount, self.user_id, self.__db_table)
        return self.__xp

    async def exp_required(self) -> int:
        """Calculates and returns the XP required to get to the next level"""
        if self.level == LEVEL_CAP:
            return 0
        return self.__xp_requirements[self.level] - self.__xp

    async def get_ranking(self) -> int:
        levels = await self.get_leaderboard()
        for i, level in enumerate(levels):
            if level[0] == self.user_id:
                return i + 1
        return -1

    async def get_leaderboard(self) -> list[tuple[int, int, int]]:
        levels = await self.__bot.database.levels.get_guild_levels(self.guild_id)
        levels.sort(key=lambda x: x[1], reverse=True)
        return levels
