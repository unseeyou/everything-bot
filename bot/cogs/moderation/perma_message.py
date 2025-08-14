import discord
from discord.ext import commands
from discord.ext.commands import Cog

from bot.bot import Bot


class PermanentMessage(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        channel_id = await self.bot.database.logs.get_log_channel(message.guild.id)
        if message.channel.id == channel_id and message.author.id == self.bot.application_id:
            await message.channel.send(message.content, embeds=message.embeds)


async def setup(bot: Bot) -> None:
    await bot.add_cog(PermanentMessage(bot))
