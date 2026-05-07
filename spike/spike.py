"""image-morpher spike — round 0 → strategy → round 1.

Validates the core hypothesis (LLM picks the right prompt strategy
from the user's preference signal, UNI-1 honors the strategy when
conditioned on the winner via image_ref) before any backend code.
See `docs/plan.md` Unit 1 for the rationale.

Run:

    cd spike && uv sync
    uv run python spike.py
    uv run python spike.py "a wolf howling at the moon"   # one-shot prompt

Reads `LUMAAI_API_KEY` and `ANTHROPIC_API_KEY` from the OS env. The
default winner is B; set `WINNER=A` to flip. The prompt can come from
a CLI arg, `SPIKE_PROMPT` env var, or the default in the config block
below.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Literal

from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from luma_agents import AsyncLuma

from system_prompt import SYSTEM_PROMPT

# API keys come from the OS env. Per-run knobs (WINNER, SPIKE_PROMPT)
# can be set in .env if you don't want to export them; existing OS env
# vars take precedence.
load_dotenv(override=False)

# Fail with a friendly message if required keys are missing, rather
# than letting the SDK clients raise KeyError on the next two lookups.
_missing = [
    k for k in ("LUMAAI_API_KEY", "ANTHROPIC_API_KEY") if not os.environ.get(k)
]
if _missing:
    sys.exit(f"missing required env var(s): {', '.join(_missing)}")

# --- config -------------------------------------------------------------

# Prompt resolution order: CLI arg → SPIKE_PROMPT env var → default.
# The CLI arg form is the convenient one for re-running the gate
# against several prompts back-to-back.
PROMPT = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.environ.get("SPIKE_PROMPT", "a vintage typewriter on a wooden desk")
)
LUMA_MODEL = os.environ.get("LUMA_MODEL", "uni-1")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

# Round 0 calls UNI-1 twice with the same prompt. If the pair comes
# back near-identical, the loop has no A/B signal — at that point edit
# this file to add prompt jitter (e.g. ", warm lighting" vs ", cool
# lighting"). The jitter axis you pick frames what dimension the user
# is voting on, so it's a deliberate edit, not a knob.

# Whether the new agents API accepts a `weight` field on image_ref
# entries is open question #2 in the plan. Probe empirically: try
# {"url": ..., "weight": 0.6} and see if the request is accepted. If
# weight is rejected (400/422), drop it and use prompt-only conditioning.
IMAGE_REF_WEIGHT: float | None = None  # set to e.g. 0.6 to probe

# UNI-1's image API is async: generations.create() enqueues a job and
# returns immediately; we poll generations.get() until state ==
# "completed". POLL_INTERVAL is how often to check (seconds);
# POLL_TIMEOUT is the overall deadline before raising
# GenerationTimeout.
POLL_INTERVAL = 2.0
POLL_TIMEOUT = 180.0


# --- errors -------------------------------------------------------------


class GenerationFailed(Exception):
    """Luma returned state=failed; .args[0] is the failure_reason."""


class GenerationTimeout(Exception):
    """Polled past the overall deadline."""


# --- types --------------------------------------------------------------

Strategy = Literal["preserve_look", "preserve_subject", "tweak"]


@dataclass
class StrategyChoice:
    rationale: str
    strategy: Strategy
    instruction: str


# --- Luma helpers -------------------------------------------------------

luma = AsyncLuma(auth_token=os.environ["LUMAAI_API_KEY"])


def _image_ref_entry(url: str) -> dict:
    entry: dict = {"url": url}
    if IMAGE_REF_WEIGHT is not None:
        entry["weight"] = IMAGE_REF_WEIGHT
    return entry


async def generate(prompt: str, image_ref: list[dict] | None = None) -> str:
    """Start a UNI-1 generation, poll to completion, return image URL."""
    kwargs: dict = {
        "prompt": prompt,
        "model": LUMA_MODEL,
        "type": "image",
        "output_format": "png",
    }
    if image_ref:
        kwargs["image_ref"] = image_ref
    gen = await luma.generations.create(**kwargs)
    deadline = time.monotonic() + POLL_TIMEOUT
    while True:
        gen = await luma.generations.get(gen.id)
        if gen.state == "completed":
            return gen.output[0].url
        if gen.state == "failed":
            raise GenerationFailed(gen.failure_reason or "unknown")
        if time.monotonic() > deadline:
            raise GenerationTimeout(
                f"generation {gen.id} did not complete in {POLL_TIMEOUT}s"
            )
        await asyncio.sleep(POLL_INTERVAL)


async def generate_with_anchor(
    choice: StrategyChoice, anchor_url: str
) -> str:
    """Round-N: generate the next image with image_ref pinned to the anchor.

    Strategy is metadata only — it informs the prompt the LLM wrote,
    not the API call shape. The new agents API has just one
    image-conditioning primitive (`image_ref`); UNI-1 reads the
    reference's role from the prompt itself.
    """
    return await generate(
        choice.instruction, image_ref=[_image_ref_entry(anchor_url)]
    )


# --- Claude strategy picker --------------------------------------------

claude = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


async def choose_strategy(
    prompt: str, winner_url: str, runner_up_url: str
) -> StrategyChoice:
    """Ask Claude which strategy to use for the next round.

    Inputs:
        prompt: the original text prompt that produced both images.
        winner_url: public Luma CDN URL of the image the user picked.
        runner_up_url: public Luma CDN URL of the other round-0 image.

    Returns a StrategyChoice with:
        rationale: 1–2 sentences on why B won (free text).
        strategy: one of preserve_look / preserve_subject / tweak.
        instruction: a self-contained text prompt for the next UNI-1
            call (NOT a constraint description — see Decision 4 in
            docs/plan.md).

    Raises ValueError if Claude's response doesn't contain parseable JSON.
    """
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
                        "text": f"Original prompt: {prompt!r}\n\nImage A (the runner-up):",
                    },
                    {"type": "image", "source": {"type": "url", "url": runner_up_url}},
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
    return StrategyChoice(
        rationale=data["rationale"],
        strategy=data["strategy"],
        instruction=data["instruction"],
    )


# --- main ---------------------------------------------------------------

# main is async because round 0 fires two UNI-1 calls in parallel via
# asyncio.gather. Sequentially each ~10–20s; concurrently ~half. The
# Luma and Anthropic SDKs return coroutines (we use AsyncLuma /
# AsyncAnthropic), which require `await`, which requires `async def`.


async def main() -> None:
    print(f"PROMPT: {PROMPT!r}")
    print()

    print("Round 0: generating A and B in parallel…")
    t0 = time.monotonic()
    # a_url and b_url are public Luma CDN URLs to the images UNI-1
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
        winner_url, runner_up_url = a_url, b_url
    else:
        winner_url, runner_up_url = b_url, a_url
    print(f"Winner (set WINNER=A or =B in .env to override): {winner_label}")
    print()

    print("Asking Claude to pick a strategy…")
    t1 = time.monotonic()
    choice = await choose_strategy(PROMPT, winner_url, runner_up_url)
    elapsed = time.monotonic() - t1
    print(f"  Rationale:    {choice.rationale}")
    print(f"  Strategy:     {choice.strategy}")
    print(f"  Instruction:  {choice.instruction!r}")
    print(f"  Claude elapsed: {elapsed:.1f}s")
    print()

    print(f"Round 1: generating new B with strategy={choice.strategy}…")
    t2 = time.monotonic()
    new_b = await generate_with_anchor(choice, anchor_url=winner_url)
    elapsed = time.monotonic() - t2
    print(f"  New B: {new_b}")
    print(f"  Round 1 elapsed: {elapsed:.1f}s")
    print()
    print("Open in a browser. Compare new B to the winner.")
    print("Did the strategy feel like the right choice?")


if __name__ == "__main__":
    asyncio.run(main())
