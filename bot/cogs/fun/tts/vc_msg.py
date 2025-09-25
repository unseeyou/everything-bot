import asyncio
import io
import os
from typing import Any

import discord
from discord.ext.commands import Cog
from google import genai
from google.genai import types

from bot.bot import Bot


class CustomPCMReader(discord.File):
    """A class to simulate a file-like object that yields your raw PCM bytes."""

    def __init__(self, raw_data_bytes: bytes, fp: str | bytes | os.PathLike[Any] | io.BufferedIOBase = "") -> None:
        super().__init__(fp)
        self.bytes_data = raw_data_bytes
        self.position = 0

    def read(self, size: int = -1) -> bytes:
        """Reads a specified number of bytes from the simulated stream."""
        if size == -1:
            size = len(self.bytes_data) - self.position

        data = self.bytes_data[self.position : self.position + size]
        self.position += len(data)
        return data

    def seek(self, offset: int) -> int:
        """Allow FFmpeg to seek (though raw streams often don't need seeking)."""
        self.position = offset
        return self.position


class Voice(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.api_key = self.bot.settings.google_api_key
        self.client = genai.Client(api_key=self.api_key)
        self.INPUT_FORMAT = "s16le"  # Signed 16-bit Little-Endian PCM
        self.SAMPLE_RATE = 24000  # 24 kHz
        self.SAMPLE_WIDTH = 2
        self.CHANNELS = 1
        self.FFMPEG_OPTIONS = {
            "before_options": (
                f"-f {self.INPUT_FORMAT} "  # Input format (Signed 16-bit Little-Endian)
                f"-ar {self.SAMPLE_RATE} "  # Sample rate (24000 Hz)
                f"-ac {self.CHANNELS} "  # Number of audio channels (e.g., 1 for mono)
                "-i pipe:0"  # Read input from stdin (standard input)
            ),
            "options": "-vn",  # No video
        }

        self.ALLOW_LIST = [650923352097292299]

    def generate(self, prompt: str) -> bytes:
        response = self.client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Umbriel",
                        ),
                    ),
                ),
            ),
        )

        return response.candidates[0].content.parts[0].inline_data.data

    async def play(self, data: bytes, voice_client: discord.VoiceClient) -> None:
        audio_source = discord.FFmpegPCMAudio(source=CustomPCMReader(data), **self.FFMPEG_OPTIONS)
        voice_client.play(audio_source, after=lambda e: self.bot.logger.error("Player error: %s", e) if e else None)
        while voice_client.is_playing():
            await asyncio.sleep(1)
        await voice_client.disconnect()

    voice_cmds = discord.app_commands.Group(
        name="vc",
        description="Voice channel/chat related commands",
    )

    @voice_cmds.command(name="tts", description="send a TTS message")
    async def tts(self, interaction: discord.Interaction, message: str) -> None:
        # sanitise message
        message = message.replace("{", "").replace("}", "").strip()
        if interaction.user.voice is None:
            await interaction.response.send_message("You are not in a voice channel!", ephemeral=True)
            return
        if interaction.user.id not in self.ALLOW_LIST:
            await interaction.response.send_message("You are not allowed to use that command!", ephemeral=True)
            return
        voice_client = await interaction.user.voice.channel.connect()
        await interaction.response.send_message("Generating audio...", ephemeral=True)
        audio_data = self.generate(message)
        await self.play(audio_data, voice_client)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Voice(bot))
