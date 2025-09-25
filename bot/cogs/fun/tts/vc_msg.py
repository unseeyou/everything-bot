import discord
from discord.ext.commands import Cog
from google import genai
from google.genai import types

from bot.bot import Bot


class Voice(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.api_key = self.bot.settings.google_api_key
        self.client = genai.Client(api_key=self.api_key)
        self.INPUT_FORMAT = "s16le"  # Signed 16-bit Little-Endian PCM
        self.SAMPLE_RATE = 24000  # 24 kHz
        self.SAMPLE_WIDTH = 2
        self.CHANNELS = 1

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

    async def play(self, data: bytes, voice_client: discord.VoiceClient) -> None: ...
