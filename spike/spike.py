"""image-morpher spike — round 0 → lever → round 1, end-to-end.

Validates the core hypothesis (LLM picks the right Luma reference
channel from the user's preference signal) before any backend code.
See `docs/plan.md` Unit 1 for the rationale.

Run:

    cd spike && uv sync && cp .env.example .env  # add API keys
    uv run python spike.py

The default winner is B; set WINNER=A in .env to flip. Re-run with
different prompts and pick decisions to gather the lever-agreement
data Unit 1's gate needs.
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

load_dotenv()

# --- config -------------------------------------------------------------

PROMPT = os.environ.get("SPIKE_PROMPT", "a vintage typewriter on a wooden desk")
PHOTON_MODEL = os.environ.get("PHOTON_MODEL", "photon-1")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# Distinct semantic seeds for round 0; the plan calls these "warm/cool
# lighting" if Photon returns near-identical pairs on the bare prompt.
SEED_A = os.environ.get("SEED_A", "warm lighting")
SEED_B = os.environ.get("SEED_B", "cool lighting")

# Per-lever weight defaults (the spike calibrates `style_ref` at
# 0.4 / 0.6 / 0.8 by re-running with WEIGHT_STYLE_REF set).
WEIGHT_STYLE_REF = float(os.environ.get("WEIGHT_STYLE_REF", "0.55"))
WEIGHT_MODIFY_IMAGE_REF = float(os.environ.get("WEIGHT_MODIFY_IMAGE_REF", "0.85"))

POLL_INTERVAL = 2.0
POLL_TIMEOUT = 180.0


# --- errors -------------------------------------------------------------


class GenerationFailed(Exception):
    """Luma returned state=failed; .args[0] is the failure_reason."""


class GenerationTimeout(Exception):
    """Polled past the overall deadline."""


# --- types --------------------------------------------------------------

Lever = Literal["style_ref", "character_ref", "modify_image_ref"]


@dataclass
class LeverChoice:
    rationale: str
    lever: Lever
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


async def generate_with_lever(choice: LeverChoice, anchor_url: str) -> str:
    """Apply the lever's reference channel to a fresh Photon call.

    `character_ref` has no weight field in the SDK; silently exempt.
    """
    if choice.lever == "style_ref":
        return await generate(
            choice.instruction,
            style_ref=[{"url": anchor_url, "weight": WEIGHT_STYLE_REF}],
        )
    if choice.lever == "character_ref":
        return await generate(
            choice.instruction,
            character_ref={"identity0": {"images": [anchor_url]}},
        )
    if choice.lever == "modify_image_ref":
        return await generate(
            choice.instruction,
            modify_image_ref={"url": anchor_url, "weight": WEIGHT_MODIFY_IMAGE_REF},
        )
    raise ValueError(f"unknown lever: {choice.lever}")


# --- Claude lever picker ------------------------------------------------

claude = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """\
You're helping refine an image generation. The user picked image B over
image A; both were generated from the same text prompt. Reason briefly
about what's better in B, then propose ONE refinement for the next round.

Choose exactly one of these reference channels:
- style_ref: preserve B's visual style, allow subject variation.
- character_ref: preserve B's subject identity, allow scene variation.
- modify_image_ref: surgical edit on B following a text instruction.

The "instruction" you return becomes the literal text prompt for the
next image generation. It MUST be a self-contained image-generation
prompt (e.g. "a vintage typewriter on a wooden desk in moodier lighting"),
NEVER a constraint description like "preserve B's mood with a similar
subject" — those become the literal Photon prompt and lose the subject.

Output JSON only, exactly this shape:
{
  "rationale": "<1-2 sentences on why B won>",
  "lever": "style_ref" | "character_ref" | "modify_image_ref",
  "instruction": "<self-contained text prompt for the next generation>"
}
"""

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


async def choose_lever(prompt: str, winner_url: str, loser_url: str) -> LeverChoice:
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
    return LeverChoice(
        rationale=data["rationale"],
        lever=data["lever"],
        instruction=data["instruction"],
    )


# --- main ---------------------------------------------------------------


async def main() -> None:
    print(f"PROMPT:           {PROMPT!r}")
    print(f"Photon model:     {PHOTON_MODEL}")
    print(f"Anthropic model:  {ANTHROPIC_MODEL}")
    print(f"Round-0 seeds:    A={SEED_A!r}  B={SEED_B!r}")
    print()

    print("Round 0: generating A and B in parallel…")
    t0 = time.monotonic()
    a_url, b_url = await asyncio.gather(
        generate(f"{PROMPT}, {SEED_A}"),
        generate(f"{PROMPT}, {SEED_B}"),
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

    print("Asking Claude to pick a lever…")
    t1 = time.monotonic()
    choice = await choose_lever(PROMPT, winner_url, loser_url)
    elapsed = time.monotonic() - t1
    print(f"  Rationale:   {choice.rationale}")
    print(f"  Lever:       {choice.lever}")
    print(f"  Instruction: {choice.instruction!r}")
    print(f"  Claude elapsed: {elapsed:.1f}s")
    print()

    print(f"Round 1: generating new B with lever={choice.lever}…")
    t2 = time.monotonic()
    new_b = await generate_with_lever(choice, anchor_url=winner_url)
    elapsed = time.monotonic() - t2
    print(f"  New B: {new_b}")
    print(f"  Round 1 elapsed: {elapsed:.1f}s")
    print()
    print("Open in a browser. Compare new B to the winner.")
    print("Did the lever feel like the right choice?")


if __name__ == "__main__":
    asyncio.run(main())
