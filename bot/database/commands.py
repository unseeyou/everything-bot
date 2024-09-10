from ast import literal_eval
from dataclasses import dataclass
from sqlite3 import IntegrityError

import aiosqlite

from bot.economy.economy_objects import Job
from bot.economy.jobs import get_job_from_str


class DatabaseIntegrityError(Exception):
    """Raised when the database returns anomalous output."""


class InfractionsRepository:
    def __init__(self, database: aiosqlite.Connection) -> None:
        self.database = database

    async def add_infraction(self, guild_id: int, admin_id: int, user_id: int, description: str) -> None:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO infractions (guild_id, admin_id, user_id, description) VALUES (?, ?, ?, ?)",
                (guild_id, admin_id, user_id, description),
            )
            await self.database.commit()

    async def get_infraction_count(self, user_id: int, guild_id: int) -> int:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "SELECT COUNT(*) FROM infractions WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id),
            )
            result = await cursor.fetchone()
            if result is None:
                return 0
            return result[0]


class LogRepository:
    def __init__(self, database: aiosqlite.Connection) -> None:
        self.database = database

    async def set_log_channel(self, guild_id: int, channel_id: int | None) -> None:
        if channel_id is None:
            async with self.database.cursor() as cursor:
                await cursor.execute(
                    "DELETE FROM log_channels WHERE guild_id = ?",
                    (guild_id,),
                )
            await self.database.commit()
            await self.database.commit()
            return
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "INSERT OR REPLACE INTO log_channels (guild_id, channel_id) VALUES (?, ?)",
                (guild_id, channel_id),
            )
        await self.database.commit()

    async def get_log_channel(self, guild_id: int) -> int | None:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "SELECT channel_id FROM log_channels WHERE guild_id = ?",
                (guild_id,),
            )
            result = await cursor.fetchone()
            if result is None:
                return None
            return result[0]


class EconomyRepository:
    def __init__(self, database: aiosqlite.Connection) -> None:
        self.database = database

    async def do_bank_interest(self) -> None:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "UPDATE bank SET bank_balance = bank_balance + ROUND(bank_balance / 20, 0)",
            )
        await self.database.commit()

    async def set_user_bank(self, user_id: int, wallet_balance: int, bank_balance: int, inventory: str) -> None:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "INSERT OR REPLACE INTO bank (user_id, wallet_balance, bank_balance, inventory) VALUES (?, ?, ?, ?)",
                (user_id, wallet_balance, bank_balance, inventory),
            )
        await self.database.commit()

    async def get_user_bank(self, user_id: int) -> tuple[int, int, str]:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "SELECT wallet_balance, bank_balance, inventory FROM bank WHERE user_id = ?",
                (user_id,),
            )
            result = await cursor.fetchone()
            if result is None:
                await cursor.execute("INSERT INTO bank (user_id) VALUES (?)", (user_id,))  # create fresh account
                return 0, 0, "[]"
            return result

    async def set_job(self, user_id: int, job: Job | None) -> None:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "INSERT OR REPLACE INTO jobs (user_id, job_name) VALUES (?, ?)",
                (user_id, job.name),
            )
        await self.database.commit()

    async def get_job(self, user_id: int) -> Job | None:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "SELECT job_name FROM jobs WHERE user_id = ?",
                (user_id,),
            )
            result = await cursor.fetchone()
            if result is None:
                return None
            return get_job_from_str(result[0])


class StaffRepository:
    def __init__(self, database: aiosqlite.Connection) -> None:
        self.database = database

    async def set_user_strikes(self, user_id: int, strikes: int) -> None:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "INSERT OR REPLACE INTO staff (user_id, strikes) VALUES (?, ?)",
                (user_id, strikes),
            )
        await self.database.commit()

    async def get_user_strikes(self, user_id: int) -> int:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "SELECT strikes FROM staff WHERE user_id = ?",
                (user_id,),
            )
            result = await cursor.fetchone()
            if result is None:
                return 0
            return result[0]


class LevelsRepository:
    def __init__(self, database: aiosqlite.Connection) -> None:
        self.database = database

    async def create_guild_levels(self, guild_id: int) -> None:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                f"""CREATE TABLE IF NOT EXISTS levels_{guild_id}(
                    user_id INTEGER PRIMARY KEY,
                    xp INTEGER DEFAULT 0
                )""",
            )
        await self.database.commit()

    async def add_levels_xp(self, amount: int, user_id: int, db_table: str) -> None:
        async with self.database.cursor() as cursor:
            try:
                await cursor.execute(
                    f"INSERT INTO {db_table} (user_id, xp) VALUES (:user_id, :amount)",  # noqa: S608
                    {"user_id": user_id, "amount": amount},
                )
                await self.database.commit()
            except IntegrityError:
                await cursor.execute(
                    f"UPDATE {db_table} SET xp = xp + :amount WHERE user_id = :user_id",  # noqa: S608
                    {"amount": amount, "user_id": user_id},
                )
                await self.database.commit()

    async def set_levels_xp(self, amount: int, user_id: int, db_table: str) -> None:
        async with self.database.cursor() as cursor:
            try:
                await cursor.execute(
                    f"INSERT INTO {db_table} (user_id, xp) VALUES (:user_id, :amount)",  # noqa: S608
                    {"user_id": user_id, "amount": amount},
                )
                await self.database.commit()
            except IntegrityError:
                await self.create_guild_levels(int("".join([i for i in db_table if i.isnumeric()])))
                await cursor.execute(
                    f"UPDATE {db_table} SET xp = :amount WHERE user_id = :user_id",  # noqa: S608
                    {"amount": amount, "user_id": user_id},
                )
                await self.database.commit()

    async def get_guild_levels(self, guild_id: int) -> list[tuple[int, int, int]]:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                f"SELECT user_id, xp FROM levels_{guild_id}",  # noqa: S608
            )
            result = await cursor.fetchall()
        return [(user_id, xp, guild_id) for user_id, xp in result]

    async def get_levels_user(self, user_id: int, guild_id: int) -> int:
        async with self.database.cursor() as cursor:
            try:
                await cursor.execute(
                    f"SELECT xp FROM levels_{guild_id} WHERE user_id = :user_id",  # noqa: S608
                    {"user_id": user_id},
                )
                result = await cursor.fetchone()
            except IntegrityError:
                await self.create_guild_levels(guild_id)
                await cursor.execute(
                    f"SELECT xp FROM levels_{guild_id} WHERE user_id = :user_id",  # noqa: S608
                    {"user_id": user_id},
                )
                result = await cursor.fetchone()
        if result is None:
            return 0
        return result[0]


class ApplicationsRepository:
    def __init__(self, database: aiosqlite.Connection) -> None:
        self.database = database

    async def get_application_roles(self, guild_id: int) -> list[tuple[str]]:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "SELECT role_name FROM application_roles WHERE role_name like ?",
                (f"%{guild_id}",),
            )
            return await cursor.fetchall()

    async def add_application_role(  # noqa: PLR0913, RUF100
        self,
        role_name: str,
        guild_id: int,
        questions: list,
        channel: int,
        role_id: int,
    ) -> None:
        questions = str(questions)
        role_name = f"{role_name}:{guild_id}"
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "INSERT OR REPLACE INTO application_roles "
                "(role_name, role_questions, output_channel, role_id) VALUES (?, ?, ?, ?)",
                (role_name, questions, channel, role_id),
            )
        await self.database.commit()

    async def remove_application_role(self, role_name: str, guild_id: int) -> None:
        role_name = f"{role_name}:{guild_id}"
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM application_roles WHERE role_name = ?",
                (role_name,),
            )
        await self.database.commit()

    async def get_application(self, role_name: str, guild_id: int) -> tuple[list, int, int]:
        role_name = f"{role_name}:{guild_id}"
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "SELECT role_questions, output_channel, role_id "
                "FROM application_roles WHERE role_name = ? COLLATE NOCASE",
                (role_name,),
            )
            result = await cursor.fetchone()
            return literal_eval(result[0]), result[1], result[2]

    async def add_application_user(self, username: str, guild_id: int, role_id: int, role_name: str) -> None:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "INSERT OR REPLACE INTO current_applications"
                " (role_name, username, guild, role_id) VALUES (?, ?, ?, ?)",
                (role_name, username, guild_id, role_id),
            )
        await self.database.commit()

    async def remove_application_user(self, username: str, guild_id: int, app_name: str) -> bool:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "SELECT COUNT(*) FROM current_applications",
            )
            before = await cursor.fetchone()
            await cursor.execute(
                "DELETE FROM current_applications WHERE username = ? AND guild = ? AND role_name = ?",
                (username, guild_id, app_name),
            )
            await cursor.execute(
                "SELECT COUNT(*) FROM current_applications",
            )
            after = await cursor.fetchone()
        await self.database.commit()
        return before != after

    async def get_application_role(self, guild_id: int, role_name: str, username: str) -> tuple[int]:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "SELECT role_id FROM current_applications WHERE guild = ? AND role_name = ? AND username = ?",
                (guild_id, role_name, username),
            )
            return await cursor.fetchone()

    async def get_application_channel(self, role_name: str) -> tuple[int]:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "SELECT output_channel FROM application_roles WHERE role_name = ? COLLATE NOCASE",
                (role_name,),
            )
            return await cursor.fetchone()


class TicketsRepository:
    def __init__(self, database: aiosqlite.Connection) -> None:
        self.database = database

    async def add_guild_ticket_data(self, guild_id: int, category_id: int) -> None:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "INSERT OR REPLACE INTO tickets (guild, category) VALUES (?, ?)",
                (guild_id, category_id),
            )
        await self.database.commit()

    async def add_guild_ticket_count(self, guild_id: int) -> None:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "UPDATE tickets SET ticket_count = ticket_count + 1 WHERE guild = ?",
                (guild_id,),
            )
        await self.database.commit()

    async def get_ticket_admins(self, guild_id: int) -> list[int]:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "SELECT admins FROM tickets WHERE guild = ?",
                (guild_id,),
            )
            data = await cursor.fetchone()
            return literal_eval(data[0])

    async def get_ticket_count(self, guild_id: int) -> int:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "SELECT ticket_count FROM tickets WHERE guild = ?",
                (guild_id,),
            )
            data = await cursor.fetchone()
            return data[0]

    async def get_ticket_category(self, guild_id: int) -> int:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "SELECT category FROM tickets WHERE guild = ?",
                (guild_id,),
            )
            data = await cursor.fetchone()
            return data[0]

    async def add_ticket_admin(self, admin_id: int, guild_id: int) -> None:
        current = await self.get_ticket_admins(guild_id=guild_id)
        current.append(admin_id)
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "UPDATE tickets SET admins = ? WHERE guild = ?",
                (str(current), guild_id),
            )
        await self.database.commit()

    async def remove_ticket_admin(self, admin_id: int, guild_id: int) -> None:
        current = list(set(await self.get_ticket_admins(guild_id=guild_id)))
        current.remove(admin_id)
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "UPDATE tickets SET admins = ? WHERE guild = ?",
                (str(current), guild_id),
            )
        await self.database.commit()

    async def remove_ticket_data(self, guild_id: int) -> None:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM tickets WHERE guild = ?",
                (guild_id,),
            )


class PetRepository:
    def __init__(self, database: aiosqlite.Connection) -> None:
        self.database = database

    async def set_current_pet(self, user_id: int, pet_name: str) -> None:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "INSERT OR REPLACE INTO pets (user_id, pet_name) VALUES (?, ?)",
                (user_id, pet_name),
            )
        await self.database.commit()

    async def get_current_pet(self, user_id: int) -> str:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "SELECT pet_name FROM pets WHERE user_id = ?",
                (user_id,),
            )
            result = await cursor.fetchone()
            if result is None:
                return "None"
            return result[0]


@dataclass
class SqliteRepository:
    """A repository that uses SQLite to store data."""

    database: aiosqlite.Connection
    infractions: InfractionsRepository = None
    logs: LogRepository = None
    tickets: TicketsRepository = None
    applications: ApplicationsRepository = None
    levels: LevelsRepository = None
    economy: EconomyRepository = None
    staff: StaffRepository = None
    pets: PetRepository = None

    async def initialize(self) -> None:
        self.infractions = InfractionsRepository(self.database)
        self.logs = LogRepository(self.database)
        self.tickets = TicketsRepository(self.database)
        self.applications = ApplicationsRepository(self.database)
        self.levels = LevelsRepository(self.database)
        self.economy = EconomyRepository(self.database)
        self.staff = StaffRepository(self.database)
        self.pets = PetRepository(self.database)

        async with self.database.cursor() as cursor:
            await cursor.execute(
                """
               CREATE TABLE IF NOT EXISTS social_media_auth_keys (
                    platform TEXT PRIMARY KEY,
                    token TEXT NOT NULL
                )
                """,
            )

            await cursor.execute(
                """
               CREATE TABLE IF NOT EXISTS jobs (
                    user_id TEXT PRIMARY KEY,
                    job_name TEXT NOT NULL
                )
                """,
            )

            await cursor.execute(
                """
               CREATE TABLE IF NOT EXISTS bank (
                    user_id INTEGER PRIMARY KEY,
                    wallet_balance INTEGER NOT NULL DEFAULT 0,
                    bank_balance INTEGER NOT NULL DEFAULT 0,
                    inventory TEXT NOT NULL DEFAULT '[]'
                )
                """,
            )

            await cursor.execute(
                """
               CREATE TABLE IF NOT EXISTS staff (
                    user_id INTEGER PRIMARY KEY,
                    strikes INTEGER NOT NULL DEFAULT 0
                )
                """,
            )

            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS log_channels (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER NOT NULL
                )
                """,
            )

            await cursor.execute(
                # role_name: ROLE_NAME:GUILD_ID
                # role_questions: list of questions to ask, will need to be loaded in like inventory
                """
                CREATE TABLE IF NOT EXISTS application_roles (
                    role_name STRING PRIMARY KEY,
                    role_questions STRING NOT NULL,
                    output_channel INTEGER NOT NULL,
                    role_id INTEGER NOT NULL
                )
                """,
            )

            await cursor.execute(
                # role_name: ROLE_NAME:GUILD_ID
                # role_questions: list of questions to ask, will need to be loaded in like inventory
                """
                CREATE TABLE IF NOT EXISTS current_applications (
                    role_name STRING PRIMARY KEY,
                    username STRING NOT NULL,
                    guild INTEGER NOT NULL,
                    role_id INTEGER NOT NULL
                )
                """,
            )

            await cursor.execute(
                # admins: list[admin ID]
                # guild: guild ID
                # category: category that tickets will be created in
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    guild INTEGER PRIMARY KEY,
                    admins STRING DEFAULT '[]',
                    category INTEGER NOT NULL,
                    ticket_count INTEGER DEFAULT 1
                )
                """,
            )

            await cursor.execute(
                # admin_id: admin user id
                # guild: guild ID
                # description: description of the infraction such as reason and punishment
                """
                CREATE TABLE IF NOT EXISTS infractions (
                    guild INTEGER PRIMARY KEY,
                    admin_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    description STRING DEFAULT 'None'
                )
                """,
            )

            await cursor.execute(
                # effects are stored as {effect: end_date}
                """
                CREATE TABLE IF NOT EXISTS effects (
                    user_id INTEGER PRIMARY KEY,
                    effects STRING DEFAULT '{}'
                )
                """,
            )

            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pets (
                    user_id INTEGER PRIMARY KEY,
                    pet_name TEXT NOT NULL DEFAULT 'None'
                )
                """,
            )

        await self.database.commit()

    async def update_auth(self, platform: str, token: str) -> None:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "INSERT OR REPLACE INTO social_media_auth_keys (platform, token) VALUES (?, ?)",
                (platform, token),
            )
        await self.database.commit()

    async def get_auth(self, platform: str) -> str | None:
        async with self.database.cursor() as cursor:
            await cursor.execute(
                "SELECT token FROM social_media_auth_keys WHERE platform = ? COLLATE NOCASE",
                (platform,),
            )
            result = await cursor.fetchone()
            if result is None:
                raise DatabaseIntegrityError
            return result[0]
