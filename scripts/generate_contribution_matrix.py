#!/usr/bin/env python3
"""
Generate a futuristic, animated GitHub contribution matrix GIF.

The data comes directly from GitHub's GraphQL API, so the visual never
inventes contribution counts. The GIF is committed to assets/ and embedded
from the profile README.
"""

import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

USER = os.environ["GITHUB_USER"]
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = Path(os.environ.get("OUTPUT", "assets/github-contribution-matrix.gif"))

QUERY = """
query($login:String!) {
  user(login:$login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
  }
}
"""

def github_data():
    payload = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "hasnain-os-contribution-matrix",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.load(response)
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]

def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def level(count, maximum):
    if count <= 0:
        return 0
    ratio = count / max(1, maximum)
    if ratio < 0.2:
        return 1
    if ratio < 0.45:
        return 2
    if ratio < 0.7:
        return 3
    return 4

calendar = github_data()
weeks = calendar["weeks"]
days = [d for week in weeks for d in week["contributionDays"]]
maximum = max((d["contributionCount"] for d in days), default=1)

W, H = 1200, 285
BG = (7, 10, 18)
GRID = (19, 29, 43)
TEXT = (215, 224, 238)
MUTED = (113, 131, 153)
CYAN = (65, 225, 255)
GOLD = (247, 194, 72)

levels = [
    (12, 18, 28),
    (16, 65, 78),
    (22, 119, 136),
    (35, 188, 202),
    (78, 230, 225),
]

cell = 14
gap = 5
step = cell + gap
grid_x = 55
grid_y = 96
grid_w = 53 * step - gap
grid_h = 7 * step - gap

# Normalize the calendar into 53 columns x 7 rows.
matrix = [[0 for _ in range(7)] for _ in range(53)]
for x, week in enumerate(weeks[-53:]):
    for day in week["contributionDays"]:
        date = datetime.fromisoformat(day["date"]).date()
        weekday = (date.weekday() + 1) % 7  # Sunday = 0
        if x < 53:
            matrix[x][weekday] = level(day["contributionCount"], maximum)

frames = []
total = calendar["totalContributions"]

for frame_index in range(20):
    reveal = min(1.0, frame_index / 15)
    scan_x = grid_x - 8 + int((grid_w + 16) * min(1.0, frame_index / 19))
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)

    # HUD frame
    draw.rounded_rectangle((18, 18, W - 18, H - 18), radius=18, outline=GRID, width=2)
    draw.line((36, 72, W - 36, 72), fill=GRID, width=1)

    title_font = font(22, True)
    small_font = font(13)
    value_font = font(15, True)

    draw.text((42, 38), "HASNAIN.OS // CONTRIBUTION MATRIX", font=title_font, fill=TEXT)
    status = "SYSTEM TELEMETRY  •  LIVE"
    draw.text((W - 250, 42), status, font=small_font, fill=CYAN)

    # Contribution cells
    for x in range(53):
        for y in range(7):
            value = matrix[x][y]
            cx = grid_x + x * step
            cy = grid_y + y * step
            if value == 0:
                fill = GRID
            else:
                # Reveal the matrix from left to right.
                if (x / 52) > reveal:
                    fill = GRID
                else:
                    fill = levels[value]
            draw.rounded_rectangle((cx, cy, cx + cell, cy + cell), radius=3, fill=fill)

    # Scan beam + top/bottom ticks.
    draw.line((scan_x, grid_y - 10, scan_x, grid_y + grid_h + 10), fill=CYAN, width=2)
    draw.line((grid_x, grid_y + grid_h + 20, grid_x + grid_w, grid_y + grid_h + 20), fill=GRID, width=1)

    # Footer telemetry.
    draw.text((55, 230), f"CONTRIBUTIONS  {total:,}", font=value_font, fill=GOLD)
    draw.text((265, 232), "ACTIVITY WINDOW  •  LAST 12 MONTHS", font=small_font, fill=MUTED)
    draw.text((W - 245, 232), "ONLINE", font=value_font, fill=CYAN)

    # Minimal pulse indicator.
    pulse = 3 + (frame_index % 4)
    draw.ellipse((W - 276, 236 - pulse, W - 268, 244 + pulse), fill=CYAN)

    frames.append(image)

OUT.parent.mkdir(parents=True, exist_ok=True)
frames[0].save(
    OUT,
    save_all=True,
    append_images=frames[1:],
    duration=140,
    loop=0,
    optimize=True,
)
print(f"Generated {OUT} for {USER}: {total} contributions")
