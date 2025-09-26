import asyncio
import io

import discord
from discord.ext.commands import Cog
from piper import PiperVoice

from bot.bot import Bot


class Voice(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.ALLOW_LIST = [650923352097292299]

        self.SAMPLE_RATE = 22050
        self.CHANNELS = 1
        self.FFMPEG_OPTIONS = {
            "before_options": (
                f"-ar {self.SAMPLE_RATE} "  # Sample rate (24000 Hz)
                f"-ac {self.CHANNELS} "  # Number of audio channels (e.g., 1 for mono)
                "-f s16le "
            ),
            "options": "-vn",  # No video
        }

    def generate(self, prompt: str) -> bytes:
        voice = PiperVoice.load("tts-model/en_GB-northern_english_male-medium.onnx")
        data = voice.synthesize(prompt)
        audio_bytes = b""
        for chunk in data:
            audio_bytes += chunk.audio_int16_bytes
        return audio_bytes

    async def play(self, data: bytes, voice_client: discord.VoiceClient) -> None:
        audio_source = discord.FFmpegPCMAudio(
            source=io.BytesIO(data),
            pipe=True,
            before_options=self.FFMPEG_OPTIONS["before_options"],
            options=self.FFMPEG_OPTIONS["options"],
        )
        voice_client.play(
            audio_source,
            after=lambda exception: self.bot.logger.exception("Player error: %s", exception) if exception else None,
        )
        while voice_client.is_playing():
            await asyncio.sleep(0.01)
        await voice_client.disconnect()

    voice_cmds = discord.app_commands.Group(
        name="vc",
        description="Voice channel/chat related commands",
    )

    @voice_cmds.command(name="tts", description="send a TTS message")
    async def tts(self, interaction: discord.Interaction, message: str) -> None:
        # sanitise message
        message = f"{interaction.user.name} said " + message.replace("{", "").replace("}", "").strip()
        if interaction.user.voice is None:
            await interaction.response.send_message("You are not in a voice channel!", ephemeral=True)
            return
        if interaction.user.id not in self.ALLOW_LIST:
            await interaction.response.send_message("You are not allowed to use that command!", ephemeral=True)
            return
        await interaction.response.send_message("Generating audio...", ephemeral=True)
        try:
            # Use asyncio.to_thread to run the blocking call without halting the event loop
            audio_data = await asyncio.to_thread(self.generate, message)
        except Exception:
            self.bot.logger.exception("Audio generation error: %s")
            await interaction.followup.send("Error generating audio.", ephemeral=True)
            return

        voice_client = await interaction.user.voice.channel.connect()
        await asyncio.sleep(0.5)
        await self.play(audio_data, voice_client)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Voice(bot))
