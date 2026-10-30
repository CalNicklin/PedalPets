"""Model of the ST7735 TN panel's slow pixels, so previews show what the eye sees.

Measured from a 120 fps phone video of the board (IMG_1788, 2026-10-30): after
a colour change a pixel is ~55% of the way there one board frame (30 ms) later
and ~95% after two, the same for brighter and darker. So what's on the glass is
a weighted mix of the last few frames drawn.
"""

import numpy as np
from PIL import Image

TAPS = (0.55, 0.40, 0.05)   # newest frame first
GHOST_LEVEL = 40            # a pixel this far (0-255) from what was drawn reads as a ghost


class Panel:
    def __init__(self, taps=TAPS):
        self.taps = taps
        self.history = []

    def show(self, img):
        """Draw `img` (RGB) and return what the panel displays this frame."""
        a = np.asarray(img.convert("RGB"), dtype=np.float32)
        self.history = [a] + self.history[:len(self.taps) - 1]
        out = np.zeros_like(a)
        for w, h in zip(self.taps, self.history):
            out += w * h
        out /= sum(self.taps[:len(self.history)])
        return Image.fromarray(out.round().astype(np.uint8))


def ghost_pixels(drawn, shown):
    """Pixels whose displayed colour is visibly off from what was drawn."""
    d = np.abs(np.asarray(drawn.convert("RGB"), dtype=np.int16) - np.asarray(shown, dtype=np.int16)).max(axis=2)
    return int((d > GHOST_LEVEL).sum())
