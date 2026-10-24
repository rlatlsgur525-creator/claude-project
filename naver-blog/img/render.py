"""HTML 도식을 PNG로 렌더한다. 사용: python3 render.py input.html output.png"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

src, out = Path(sys.argv[1]).resolve(), sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 860, "height": 600}, device_scale_factor=2)
    pg.goto(src.as_uri())
    pg.wait_for_timeout(300)
    pg.locator("body").screenshot(path=out)
    b.close()
print(out)
