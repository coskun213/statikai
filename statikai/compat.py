"""Font discovery without assuming a Linux filesystem."""
import os
from functools import lru_cache
from pathlib import Path
from PIL import ImageFont


@lru_cache(maxsize=32)
def load_font(size=19, serif=False):
    explicit = os.environ.get('STATIKAI_FONT')
    if explicit:
        return ImageFont.truetype(explicit, size)
    names = ['DejaVuSerif.ttf', 'times.ttf', 'Times New Roman.ttf', 'Times.ttc'] if serif else ['DejaVuSans.ttf', 'arial.ttf', 'Arial.ttf', 'Helvetica.ttc']
    folders = [Path('/usr/share/fonts/truetype/dejavu'),
               Path(os.environ.get('WINDIR', 'C:/Windows'))/'Fonts',
               Path('/System/Library/Fonts/Supplemental'), Path('/Library/Fonts')]
    for name in names:
        for candidate in [name, *(str(folder/name) for folder in folders)]:
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                pass
    return ImageFont.load_default(size=size)
