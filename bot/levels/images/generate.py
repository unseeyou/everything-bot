import io

from discord import File
from PIL import Image, ImageDraw, ImageFont


def create_level_icon(level: int, id: int) -> File:
    img = Image.open("LEVEL.png")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(100)
    level = str(level)
    if len(level) == 1:
        pos = (220, 185)
    elif len(level) == 2:  # noqa: PLR2004
        pos = (190, 185)
    else:
        pos = (160, 185)
    draw.text(pos, level, font=font, fill=(0, 75, 39))

    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)

    return File(img_buffer, filename=f"level_icon_{id}.png")
