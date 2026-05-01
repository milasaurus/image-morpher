"""image-morpher spike — round 0 → reference channel → round 1.

Validates the core hypothesis (LLM picks the right Luma reference
channel from the user's preference signal) before any backend code.
See `docs/plan.md` Unit 1 for the rationale.

Run:

    cd spike && uv sync
    uv run python spike.py

Reads `LUMAAI_API_KEY` and `ANTHROPIC_API_KEY` from the OS env. The
default winner is B; set `WINNER=A` to flip. Other knobs (prompt,
model, weights) are likewise OS env vars — see config block below.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Literal

from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from lumaai import AsyncLumaAI

from system_prompt import SYSTEM_PROMPT

# API keys come from the OS env. Per-run knobs (WINNER, SPIKE_PROMPT,
# weights) can be set in .env if you don't want to export them; existing
# OS env vars take precedence.
load_dotenv(override=False)

# --- config -------------------------------------------------------------

PROMPT = os.environ.get("SPIKE_PROMPT", "a vintage typewriter on a wooden desk")
PHOTON_MODEL = os.environ.get("PHOTON_MODEL", "photon-1")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# Round 0 calls Photon twice with the same prompt. If the pair comes
# back near-identical, the loop has no A/B signal — at that point edit
# this file to add prompt jitter (e.g. ", warm lighting" vs ", cool
# lighting"). The jitter axis you pick frames what dimension the user
# is voting on, so it's a deliberate edit, not a knob.

# Per-channel weight defaults (the spike calibrates `style_ref` at
# 0.4 / 0.6 / 0.8 by re-running with WEIGHT_STYLE_REF set).
WEIGHT_STYLE_REF = float(os.environ.get("WEIGHT_STYLE_REF", "0.55"))
WEIGHT_MODIFY_IMAGE_REF = float(os.environ.get("WEIGHT_MODIFY_IMAGE_REF", "0.85"))

# Photon's image API is async: create() enqueues a job and returns
# immediately; we poll generations.get() until state == "completed".
# POLL_INTERVAL is how often to check (seconds); POLL_TIMEOUT is the
# overall deadline before raising GenerationTimeout. Photon usually
# completes in 10–20s, so 180s is a generous safety net for stuck jobs.
POLL_INTERVAL = 2.0
POLL_TIMEOUT = 180.0


# --- errors -------------------------------------------------------------


class GenerationFailed(Exception):
    """Luma returned state=failed; .args[0] is the failure_reason."""


class GenerationTimeout(Exception):
    """Polled past the overall deadline."""


# --- types --------------------------------------------------------------

RefChannel = Literal["style_ref", "character_ref", "modify_image_ref"]


@dataclass
class RefChannelChoice:
    rationale: str
    ref_channel: RefChannel
    instruction: str


# --- Luma helpers -------------------------------------------------------

luma = AsyncLumaAI(auth_token=os.environ["LUMAAI_API_KEY"])


async def generate(prompt: str, **refs) -> str:
    """Start a Photon generation, poll to completion, return image URL."""
    gen = await luma.generations.image.create(
        prompt=prompt,
        model=PHOTON_MODEL,
        **refs,
    )
    deadline = time.monotonic() + POLL_TIMEOUT
    while True:
        gen = await luma.generations.get(id=gen.id)
        if gen.state == "completed":
            return gen.assets.image
        if gen.state == "failed":
            raise GenerationFailed(gen.failure_reason or "unknown")
        if time.monotonic() > deadline:
            raise GenerationTimeout(
                f"generation {gen.id} did not complete in {POLL_TIMEOUT}s"
            )
        await asyncio.sleep(POLL_INTERVAL)


async def generate_with_ref_channel(
    choice: RefChannelChoice, anchor_url: str
) -> str:
    """Apply the chosen reference channel to a fresh Photon call.

    `character_ref` has no weight field in the SDK; silently exempt.
    """
    if choice.ref_channel == "style_ref":
        return await generate(
            choice.instruction,
            style_ref=[{"url": anchor_url, "weight": WEIGHT_STYLE_REF}],
        )
    if choice.ref_channel == "character_ref":
        return await generate(
            choice.instruction,
            character_ref={"identity0": {"images": [anchor_url]}},
        )
    if choice.ref_channel == "modify_image_ref":
        return await generate(
            choice.instruction,
            modify_image_ref={"url": anchor_url, "weight": WEIGHT_MODIFY_IMAGE_REF},
        )
    raise ValueError(f"unknown reference channel: {choice.ref_channel}")


# --- Claude reference-channel picker ------------------------------------

claude = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


async def choose_ref_channel(
    prompt: str, winner_url: str, loser_url: str
) -> RefChannelChoice:
    msg = await claude.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Original prompt: {prompt!r}\n\nImage A (the loser):",
                    },
                    {"type": "image", "source": {"type": "url", "url": loser_url}},
                    {"type": "text", "text": "Image B (the winner):"},
                    {"type": "image", "source": {"type": "url", "url": winner_url}},
                ],
            }
        ],
    )
    text = "".join(block.text for block in msg.content if block.type == "text")
    m = _JSON_RE.search(text)
    if not m:
        raise ValueError(f"no JSON in LLM response: {text!r}")
    data = json.loads(m.group(0))
    return RefChannelChoice(
        rationale=data["rationale"],
        ref_channel=data["ref_channel"],
        instruction=data["instruction"],
    )


# --- main ---------------------------------------------------------------


async def main() -> None:
    print(f"PROMPT: {PROMPT!r}")
    print()

    print("Round 0: generating A and B in parallel…")
    t0 = time.monotonic()
    # a_url and b_url are public Luma CDN URLs to the images Photon
    # just generated — Claude fetches them directly in the next step.
    a_url, b_url = await asyncio.gather(
        generate(PROMPT),
        generate(PROMPT),
    )
    elapsed = time.monotonic() - t0
    print(f"  A: {a_url}")
    print(f"  B: {b_url}")
    print(f"  Round 0 elapsed: {elapsed:.1f}s")
    print()

    winner_label = os.environ.get("WINNER", "B").upper()
    if winner_label == "A":
        winner_url, loser_url = a_url, b_url
    else:
        winner_url, loser_url = b_url, a_url
    print(f"Winner (set WINNER=A or =B in .env to override): {winner_label}")
    print()

    print("Asking Claude to pick a reference channel…")
    t1 = time.monotonic()
    choice = await choose_ref_channel(PROMPT, winner_url, loser_url)
    elapsed = time.monotonic() - t1
    print(f"  Rationale:    {choice.rationale}")
    print(f"  Ref channel:  {choice.ref_channel}")
    print(f"  Instruction:  {choice.instruction!r}")
    print(f"  Claude elapsed: {elapsed:.1f}s")
    print()

    print(f"Round 1: generating new B with ref_channel={choice.ref_channel}…")
    t2 = time.monotonic()
    new_b = await generate_with_ref_channel(choice, anchor_url=winner_url)
    elapsed = time.monotonic() - t2
    print(f"  New B: {new_b}")
    print(f"  Round 1 elapsed: {elapsed:.1f}s")
    print()
    print("Open in a browser. Compare new B to the winner.")
    print("Did the reference channel feel like the right choice?")


if __name__ == "__main__":
    asyncio.run(main())
