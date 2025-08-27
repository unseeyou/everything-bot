import asyncio

from bot.bot import Bot


async def main() -> None:
    await bot.load_extensions("bot/cogs")
    await bot.connect_to_database()
    await bot.database.create_tables()
    bot.logger.info("Database Tables Created")
    await bot.start(bot.settings.discord_bot_token)


async def shutdown() -> None:
    await bot.close_database_connection()
    await bot.close()


if __name__ == "__main__":
    bot = Bot()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        bot.logger.info("Shutting down bot...")
    finally:
        loop.run_until_complete(shutdown())
        loop.stop()
        loop.close()
