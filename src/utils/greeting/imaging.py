"""Image processing utilities."""
from PIL import Image, ImageChops, ImageDraw
import requests

def download_background(url):
    """Download a background image from the specified URL."""
    response = requests.get(url)
    if response.status_code == 200:
        background_filename = "../background.png"
        with open(background_filename, "wb") as f:
            f.write(response.content)
        return background_filename
    else:
        return None

def circle(pfp, size=(215, 215)):
    """Create a circular profile picture."""
    pfp = pfp.resize(size, Image.LANCZOS).convert("RGBA")
    bigsize = (pfp.size[0] * 3, pfp.size[1] * 3)
    mask = Image.new('L', bigsize, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + bigsize, fill=255)
    mask = mask.resize(pfp.size, Image.LANCZOS)
    mask = ImageChops.darker(mask, pfp.split()[-1])
    pfp.putalpha(mask)
    return pfp

# Add other image processing functions here
