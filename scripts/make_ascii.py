"""Convert a photo to an ASCII portrait PNG (dark background, light characters).
Usage: python scripts/make_ascii.py photo.jpg assets/portrait.png [cols]
"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

src, out = sys.argv[1], sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 110
CROP = None  # (left, top, right, bottom) -> set below if desired
if len(sys.argv) > 7:
    CROP = tuple(int(v) for v in sys.argv[4:8])

RAMP = " .:-=+*#%@"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FS = 14
font = ImageFont.truetype(FONT, FS)
cw = font.getlength("M")
ch = FS * 1.15

img = Image.open(src).convert("L")
if CROP:
    img = img.crop(CROP)
import cv2, numpy as np
a = np.array(img)
a = (255 * (a / 255.0) ** 0.55).astype(np.uint8)  # lift dark tones
a = cv2.GaussianBlur(a, (0, 0), 1.5)
a = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4)).apply(a)
# blend luminance with edges so eyes, brows, nose and beard line stay readable
edges = cv2.Canny(a, 40, 110).astype(np.float32)
edges = cv2.GaussianBlur(edges, (0, 0), 1.0)
mix = 0.9 * a.astype(np.float32) + 0.5 * edges
mix = np.clip(mix, 0, 255).astype(np.uint8)
img = ImageOps.autocontrast(Image.fromarray(mix), cutoff=2)

rows = int(cols * (img.height / img.width) * (cw / ch))
small = img.resize((cols, rows), Image.LANCZOS)

lines = []
for y in range(rows):
    line = ""
    for x in range(cols):
        v = small.getpixel((x, y)) / 255
        v = v ** 1.4
        line += RAMP[int(v * (len(RAMP) - 1))]
    lines.append(line.rstrip())

pad = 16
W = int(cw * cols) + pad * 2
H = int(ch * rows) + pad * 2
canvas = Image.new("RGB", (W, H), (13, 17, 23))  # GitHub dark bg
d = ImageDraw.Draw(canvas)
for i, l in enumerate(lines):
    d.text((pad, pad + i * ch), l, font=font, fill=(201, 209, 217))
canvas.save(out)
print(canvas.size)
open(out.rsplit(".", 1)[0] + ".txt", "w").write("\n".join(lines))
