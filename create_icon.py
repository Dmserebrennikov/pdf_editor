"""
Create PDF Editor icon (icon.ico) for the desktop shortcut.
Run once: py create_icon.py
"""
from PIL import Image, ImageDraw, ImageFont

# Build icon at 256x256 then downscale for .ico
size = 256
img = Image.new("RGB", (size, size), color=(255, 255, 255))
draw = ImageDraw.Draw(img)

# Document shape: rectangle with folded corner
margin = 24
doc_color = (220, 220, 225)
fold_color = (200, 200, 210)
draw.rectangle([margin, margin, size - margin, size - margin], fill=doc_color, outline=(160, 160, 170))
# Folded corner (triangle)
fold = 48
draw.polygon(
    [
        (size - margin - fold, margin),
        (size - margin, margin),
        (size - margin, margin + fold),
    ],
    fill=fold_color,
    outline=(160, 160, 170),
)
# Red PDF accent bar (top)
draw.rectangle([margin, margin, size - margin - fold, margin + 12], fill=(180, 50, 50))
# "PDF" text - try default font, fallback to simple draw
try:
    font = ImageFont.truetype("arial.ttf", 52)
except OSError:
    font = ImageFont.load_default()
text = "PDF"
# Center text in document area
bbox = draw.textbbox((0, 0), text, font=font)
tw = bbox[2] - bbox[0]
th = bbox[3] - bbox[1]
x = (size - tw) // 2
y = (size - th) // 2 - 10
draw.text((x, y), text, fill=(80, 80, 90), font=font)

# Save as ICO with multiple sizes for Windows
sizes = [(256, 256), (48, 48), (32, 32), (16, 16)]
img.save("icon.ico", format="ICO", sizes=sizes)
print("Created icon.ico")
