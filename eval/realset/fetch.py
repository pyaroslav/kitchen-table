"""Real-world set: 9 real letters and notices, fetched from their official sources.

The files are NOT in this repo. Most are US federal works (public domain), but the
two deed mailers and the Pennsylvania model notice aren't clearly public domain, so
this script downloads everything from the original publisher, renders the page(s) a
person would actually photograph, and makes the same kind of "phone photo" as the
synthetic set. Output: eval/realset/cache/ (git-ignored).

    python eval/realset/fetch.py        # needs curl and pdftoppm (poppler-utils)
"""

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
CACHE = HERE / "cache"
sys.path.insert(0, str(HERE.parent))
from make_letters import phoneify  # noqa: E402

SOURCES = json.loads((HERE / "truth.json").read_text())["letters"]


def main():
    CACHE.mkdir(exist_ok=True)
    for i, (lid, s) in enumerate(SOURCES.items()):
        raw = CACHE / f"{lid}.src{Path(s['url'].split('?')[0]).suffix.lower() or '.pdf'}"
        if not raw.exists():
            subprocess.run(["curl", "-sfL", "-A", "Mozilla/5.0", "-o", str(raw), s["url"]], check=True)
        pngs = []
        if raw.suffix == ".pdf" and s.get("extract_image"):
            # The letter is a picture inside a press-release PDF: take the largest embedded image.
            stem = CACHE / f"{lid}.img"
            subprocess.run(["pdfimages", "-png", "-f", "1", "-l", "1", str(raw), str(stem)], check=True)
            biggest = max(CACHE.glob(f"{lid}.img-*.png"), key=lambda f: f.stat().st_size)
            png = CACHE / f"{lid}.p1.png"
            Image.open(biggest).convert("RGB").save(png)
            pngs.append(png)
        elif raw.suffix == ".pdf":
            for page in s["pages"]:
                out = CACHE / f"{lid}.p{page}"
                subprocess.run(["pdftoppm", "-r", "150", "-png", "-singlefile", "-f", str(page), "-l", str(page),
                                str(raw), str(out)], check=True)
                pngs.append(Path(f"{out}.png"))
        else:
            png = CACHE / f"{lid}.p1.png"
            Image.open(raw).convert("RGB").save(png)
            pngs.append(png)
        photos = []
        for n, png in enumerate(pngs):
            dst = CACHE / f"{lid}.p{n + 1}.photo.jpg"
            if s.get("already_a_photo"):
                Image.open(png).convert("RGB").save(dst, "JPEG", quality=85)
            else:
                phoneify(png, dst, seed=500 + i * 10 + n)
            photos.append(dst.name)
        print(lid, photos)


if __name__ == "__main__":
    main()
