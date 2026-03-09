"""
Generate icon.ico from thumbnail.png (for the desktop shortcut).
Place thumbnail.png in this folder and run: py create_icon_from_thumbnail.py
"""
from pathlib import Path

from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
THUMBNAIL_PATH = SCRIPT_DIR / "thumbnail.png"
ICON_PATH = SCRIPT_DIR / "icon.ico"
SIZES = [(256, 256), (48, 48), (32, 32), (16, 16)]


def main() -> None:
    if not THUMBNAIL_PATH.exists():
        print(f"Error: {THUMBNAIL_PATH} not found. Add thumbnail.png to the project folder.")
        return
    img = Image.open(THUMBNAIL_PATH)
    img = img.convert("RGBA")
    # Make square by cropping/padding to center (use longer side)
    w, h = img.size
    if w != h:
        side = max(w, h)
        new = Image.new("RGBA", (side, side), (255, 255, 255, 0))
        x = (side - w) // 2
        y = (side - h) // 2
        new.paste(img, (x, y))
        img = new
    # Resize to 256 for ICO (Windows uses largest for scaling)
    if img.size[0] != 256 or img.size[1] != 256:
        img = img.resize((256, 256), Image.Resampling.LANCZOS)
    img.save(ICON_PATH, format="ICO", sizes=SIZES)
    print(f"Created {ICON_PATH} from thumbnail.png")


if __name__ == "__main__":
    main()
