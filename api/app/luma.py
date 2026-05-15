import asyncio
import time

from luma_agents import AsyncLuma

from app.config import settings
from app.constants import POLL_INTERVAL_S, POLL_TIMEOUT_S


class GenerationFailed(Exception):
    """Luma returned state=failed; .args[0] is the failure_reason."""


class GenerationTimeout(Exception):
    """Polled past the overall deadline."""

_client = AsyncLuma(auth_token=settings.LUMAAI_API_KEY)


def _image_ref_entry(url: str) -> dict:
    entry: dict = {"url": url}
    if settings.IMAGE_REF_WEIGHT is not None:
        entry["weight"] = settings.IMAGE_REF_WEIGHT
    return entry


async def generate(prompt: str, image_ref: list[dict] | None = None) -> str:
    """Start a UNI-1 generation, poll to completion, return image URL."""
    kwargs: dict = {
        "prompt": prompt,
        "model": settings.LUMA_MODEL,
        "type": "image",
        "output_format": "png",
        "aspect_ratio": "1:1",
    }
    if image_ref:
        kwargs["image_ref"] = image_ref

    gen = await _client.generations.create(**kwargs)
    deadline = time.monotonic() + POLL_TIMEOUT_S

    while True:
        gen = await _client.generations.get(gen.id)
        if gen.state == "completed":
            return gen.output[0].url
        if gen.state == "failed":
            raise GenerationFailed(gen.failure_reason or "unknown")
        if time.monotonic() > deadline:
            raise GenerationTimeout(f"generation {gen.id} did not complete in {POLL_TIMEOUT_S}s")
        await asyncio.sleep(POLL_INTERVAL_S)


async def edit(source_url: str, instruction: str) -> str:
    """Image edit: apply instruction while preserving everything not mentioned."""
    kwargs: dict = {
        "type": "image_edit",
        "source": {"url": source_url},
        "prompt": instruction,
        "model": settings.LUMA_MODEL,
        "output_format": "png",
    }
    gen = await _client.generations.create(**kwargs)
    deadline = time.monotonic() + POLL_TIMEOUT_S

    while True:
        gen = await _client.generations.get(gen.id)
        if gen.state == "completed":
            return gen.output[0].url
        if gen.state == "failed":
            raise GenerationFailed(gen.failure_reason or "unknown")
        if time.monotonic() > deadline:
            raise GenerationTimeout(f"generation {gen.id} did not complete in {POLL_TIMEOUT_S}s")
        await asyncio.sleep(POLL_INTERVAL_S)
