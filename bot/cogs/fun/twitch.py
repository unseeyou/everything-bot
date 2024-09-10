import asyncio
import contextlib
import datetime
import json
import logging
from json import JSONDecodeError

import aiohttp
import discord
from aiofiles import open as aopen
from discord import app_commands, utils
from discord.ext import commands, tasks

from bot.bot import Bot


async def get_auth_token(bot: Bot) -> bool:
    data = {
        "code": "channel:view:*",
        "grant_type": "client_credentials",
        "redirect_uri": "http://localhost",
        "client_id": bot.settings.twitch_client_id,
        "client_secret": bot.settings.twitch_secret,
    }
    endpoint = "https://id.twitch.tv/oauth2/token"

    async with aiohttp.ClientSession() as session, session.post(endpoint, data=data) as response:
        authcode = await response.json()
        authcode = authcode["access_token"]

    await bot.database.update_auth("twitch", authcode)

    return True


async def check_live(channel_name: str, bot: Bot) -> None | dict | bool:
    # get OAUTH2
    authcode: str = await bot.database.get_auth("twitch")
    client_id = bot.settings.twitch_client_id

    params = {"user_login": channel_name.lower()}
    endpoint = "https://api.twitch.tv/helix/streams"
    async with aiohttp.ClientSession() as session:
        channel = await session.get(
            endpoint,
            headers={"Authorization": "Bearer " + authcode, "Client-Id": client_id},
            params=params,
        )
    data = await channel.json()

    if not data["data"]:
        return False

    elif data["data"][0]["type"] == "live":  # noqa: RET505
        return data["data"][0]
    return None


async def create_embed(result: dict) -> discord.Embed:
    embed = discord.Embed(
        title=result["title"],
        url=f'https://twitch.tv/{result["user_login"]}',
        colour=discord.Colour.dark_purple(),
    )
    embed.set_image(url=result["thumbnail_url"].replace("-{width}x{height}", ""))
    embed.set_author(name=result["user_name"])  # url=result["profile_url"]
    embed.set_footer(
        text=f"stream started at {result["started_at"]
                                  .replace("-", "/")
                                  .replace("T", ", ")
                                  .replace("Z", "") + " UTC +0"}",
    )
    embed.set_thumbnail(url=f"https://static-cdn.jtvnw.net/ttv-boxart/{result['game_id']}.jpg")
    embed.add_field(name="Playing", value=result["game_name"])
    # date stuff
    stream_time = result["started_at"]
    year = int(stream_time[:4])
    month = int(stream_time[5:7])
    day = int(stream_time[8:10])
    hour = int(stream_time[11:13])
    second = int(stream_time[14:16])
    date = int(
        datetime.datetime(year=year, month=month, day=day, hour=hour, second=second, tzinfo=datetime.UTC).timestamp(),
    )

    embed.add_field(name="Stream Started", value=f"<t:{date}:R>")
    return embed


async def send_message(  # noqa: PLR0913
    embed: discord.Embed,
    channel: discord.TextChannel,
    message: discord.Message,
    result: dict,
    ping_role: discord.Role,
    user: str,
) -> None:
    uid = result["started_at"].replace("-", "/").replace("T", ", ").replace("Z", "")  # unique identifier
    notif_msg = message.replace("[PING]", f"{ping_role.mention}").replace("[USER]", user)
    embeds = [msg.embeds async for msg in channel.history(limit=50)]
    messages = []
    button = discord.ui.Button(
        label="Watch on Twitch",
        url=f"https://twitch.tv/{result['user_login']}",
        style=discord.ButtonStyle.url,
    )
    view = discord.ui.View()
    view.add_item(button)

    for i in embeds:
        with contextlib.suppress(IndexError):
            messages.append(str(i[0].footer))

    if messages:
        if f"EmbedProxy(text='stream started at {uid} UTC +0')" in messages:
            pass
        else:
            await channel.send(notif_msg, embed=embed, view=view)
    else:
        await channel.send(notif_msg, embed=embed, view=view)


class TwitchStuff(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.live_notifs_loop.start()
        self.update_auth.start()

    def cog_unload(self) -> None:
        self.live_notifs_loop.cancel()
        self.update_auth.cancel()

    @tasks.loop(seconds=30)
    async def live_notifs_loop(self) -> None:
        async with aopen("streamers.json", "r") as file:
            content = await file.read()
            json_file = json.loads(content)
            await file.close()
            # Makes sure the json isn't empty before continuing.
            if json_file is not None:
                pass
            else:
                logging.warning("streamers.json file is empty")
            # iterate over each server
            for streamer in json_file:
                if len(streamer) > 0:
                    output = await check_live(streamer, bot=self.bot)
                    if output:
                        embed = await create_embed(result=output)
                        for guild in json_file[streamer]:
                            server: discord.Guild = self.bot.get_guild(int(guild["serverID"]))
                            channel = utils.get(server.text_channels, id=guild["ChannelID"])
                            await send_message(
                                embed=embed,
                                channel=channel,
                                ping_role=server.get_role(guild["pingroleID"]),
                                result=output,
                                message=guild["message"],
                                user=output["user_name"],
                            )

    @tasks.loop(seconds=360)
    async def update_auth(self) -> None:
        await get_auth_token(self.bot)

    @live_notifs_loop.before_loop
    async def before_live_notifs(self) -> None:
        logging.info("initiating twitch notifs...")
        while not self.bot.is_ready():
            await asyncio.sleep(1)
        logging.info("twitch notifs initiated")

    twitch = app_commands.Group(name="twitch", description="twitch notifications")

    @twitch.command(description="custom twitch notifications")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(
        streamer_names="all the streamers you want notifications for separated by commas",
        notif_channel="the text channel the notification will be sent to",
        message="the message sent, using [USER] as where the name goes & [PING] as where the ping goes",
        ping_role="the role being pinged in the notification [optional, otherwise @everyone ping]",
    )
    async def add_live_alerts(  # noqa: PLR0913, RUF100
        self,
        interaction: discord.Interaction,
        streamer_names: str,
        notif_channel: discord.TextChannel,
        message: str,
        ping_role: discord.Role,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        server_details = {
            "serverID": interaction.guild_id,
            "ChannelID": notif_channel.id,
            "message": message,
            "pingroleID": ping_role.id,
        }  # new structure only searches for each streamer once per cycle instead of multiple times
        async with aopen("streamers.json", "r") as file:
            try:
                content = await file.read()
                json_file = json.loads(content)
            except JSONDecodeError:
                json_file = {}
            for streamer in list(
                {l.strip() for l in streamer_names.split(",")},  # noqa: E741
            ):  # if a user puts a streamer more than once we don't want
                try:  # messages getting sent, so this prevents it.
                    for srvr in json_file[streamer]:  # replace the data for that server
                        if srvr["serverID"] == server_details["serverID"]:
                            json_file[streamer][json_file[streamer].index(srvr)] = server_details
                        else:
                            json_file[streamer] = json_file[streamer].append(
                                server_details,
                            )  # if streamer already exists just append to the list
                except KeyError:
                    json_file[streamer] = [server_details]  # otherwise just make a new list
        async with aopen("streamers.json", "w") as write_file:
            json_file = json.dumps(json_file, indent=4)  # makes the json pretty (gives proper formatting)
            await write_file.write(str(json_file))  # same here
            await write_file.close()
        await interaction.followup.send("Alert/s added successfully!")

    @twitch.command(description="clears the live notifications for current server")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear_live_notifications(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        async with aopen("streamers.json", "r") as file:
            content = await file.read()
            json_file = json.loads(content)
            for streamer in json_file:
                for server in json_file[streamer]:
                    if server["serverID"] == interaction.guild_id:
                        json_file[streamer].remove(server)
            await file.close()
        async with aopen("streamers.json", "w") as write_file:
            json_file = json.dumps(json_file, indent=4)  # makes the json pretty (gives proper formatting)
            await write_file.write(str(json_file))  # python uses "'"s in dicts
            await write_file.close()
        await interaction.followup.send(
            "Alerts removed! Please create a post in the forum of my help server if it did not work. (/server for "
            "invite)",
        )

    @twitch.command(description="removed the live notifications for a specific streamer")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def remove_live_notification(self, interaction: discord.Interaction, streamer: str) -> None:
        await interaction.response.defer(ephemeral=True)
        async with aopen("streamers.json", "r") as file:
            content = await file.read()
            json_file = json.loads(content)
            for s in json_file:
                if s.lower() == streamer.lower():
                    for server in json_file[s]:
                        if server["serverID"] == interaction.guild_id:
                            json_file[s].remove(server)
            await file.close()

        async with aopen("streamers.json", "w") as write_file:
            json_file = json.dumps(json_file, indent=4)  # makes the json pretty (gives proper formatting)
            await write_file.write(str(json_file))  # python uses "'"s in dicts

            await write_file.close()
        await interaction.followup.send(
            "Alerts removed! Please create a post in the forum of my help server if it did not work. (/server for "
            "invite)",
        )


async def setup(bot: Bot) -> None:
    await bot.add_cog(TwitchStuff(bot))
