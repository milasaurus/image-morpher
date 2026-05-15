#!/usr/bin/env python3
"""
Run a 5-round image-morpher session and export an MP4.

Usage:
  uv run --with pillow python3 assets/morph_run.py
  uv run --with pillow python3 assets/morph_run.py "your custom prompt here"
"""

import json, sys, time, urllib.request, subprocess, os
from datetime import datetime
from PIL import Image
from io import BytesIO

API = "http://localhost:8001"

DEFAULT_PROMPT = (
    "A battle-worn mixed-race woman — sharp cheekbones, deep brown skin with warm "
    "undertones, cropped natural hair slicked back by rain — stands motionless at the "
    "edge of a crumbling overpass in a submerged Neo-Tokyo, 2087. Cybernetic implants "
    "trace her jawline and left temple, faintly luminescent. Below, flood canals choked "
    "with debris reflect fractured neon — kanji signage in hot pink, acid green, electric "
    "teal — rippling across oily black water. Crowds in surgical masks push through narrow "
    "market stalls beneath her, hawking stripped drone parts and bootleg augments. Behind "
    "her, Shinjuku's megastructures rise in brutal concrete tiers, their upper floors lost "
    "in a low amber smog layer. Rain falls in sheets, catching the light of a massive "
    "rotating Asahi hologram. Her coat — layered, asymmetric, scorched at the hem — whips "
    "in the updraft from a passing cargo drone. Expression unreadable. Cinematic wide shot, "
    "anamorphic 2.39:1, shallow depth of field pulling focus to her face, volumetric smog "
    "light, hyper-detailed, photorealistic, Ghost in the Shell meets Blade Runner 2049 "
    "color grading."
)

STRATEGIES = ["tweak", "preserve_look", "preserve_subject", "tweak"]

LABEL = {
    "tweak": "Refine this",
    "preserve_look": "New subject, same look",
    "preserve_subject": "New scene, same subject",
}

PROMPT = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT

# Timestamped output paths so runs never overwrite each other
RUN_ID    = datetime.now().strftime("%Y%m%d_%H%M%S")
REPO      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_DIR = os.path.join(REPO, "assets")
FRAME_DIR = os.path.join(ASSET_DIR, f"frames_{RUN_ID}")
OUT_MP4   = os.path.join(ASSET_DIR, f"evolution_{RUN_ID}.mp4")

os.makedirs(FRAME_DIR, exist_ok=True)


def post(body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{API}/api/round", data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=200) as r:
        return json.loads(r.read())


def fetch_and_save(url, path):
    with urllib.request.urlopen(url, timeout=30) as r:
        img = Image.open(BytesIO(r.read())).convert("RGB")
    img.save(path, format="PNG")
    return path


frame_paths = []
winner = runner_up = None

print(f"Prompt: {PROMPT[:80]}…\n", flush=True)

# Round 0
print("Round 0: generating two images…", flush=True)
t = time.time()
d = post({"prompt": PROMPT})
print(f"  {time.time()-t:.0f}s", flush=True)
winner    = d["images"][0]
runner_up = d["images"][1]
p = fetch_and_save(winner, os.path.join(FRAME_DIR, "frame_00_round0.png"))
frame_paths.append(p)

# Rounds 1–4
for i, strategy in enumerate(STRATEGIES, 1):
    print(f"Round {i}: {LABEL[strategy]}…", flush=True)
    t = time.time()
    d = post({"prompt": PROMPT, "winner_url": winner,
              "runner_up_url": runner_up, "strategy": strategy})
    print(f"  {time.time()-t:.0f}s  →  {d.get('instruction','')[:90]}", flush=True)
    runner_up = winner
    winner    = d["images"][0]
    slug = LABEL[strategy].lower().replace(" ", "_").replace(",", "")
    p = fetch_and_save(winner, os.path.join(FRAME_DIR, f"frame_0{i}_{slug}.png"))
    frame_paths.append(p)

# Build MP4
print("\nBuilding MP4…", flush=True)
concat = os.path.join(FRAME_DIR, "concat.txt")
with open(concat, "w") as f:
    for p in frame_paths:
        f.write(f"file '{p}'\nduration 2.5\n")
    f.write(f"file '{frame_paths[-1]}'\n")

subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat,
    "-vf", "scale=1024:1024:flags=lanczos",
    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
    OUT_MP4,
], check=True, capture_output=True)

print(f"\nFrames: {FRAME_DIR}/")
print(f"MP4:    {OUT_MP4}")
