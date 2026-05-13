import asyncio
import time

from luma_agents import AsyncLuma

from app.config import settings


class GenerationFailed(Exception):
    """Luma returned state=failed; .args[0] is the failure_reason."""


class GenerationTimeout(Exception):
    """Polled past the overall deadline."""


_POLL_INTERVAL = 2.0
_POLL_TIMEOUT = 180.0

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
    }
    if image_ref:
        kwargs["image_ref"] = image_ref

    gen = await _client.generations.create(**kwargs)
    deadline = time.monotonic() + _POLL_TIMEOUT

    while True:
        gen = await _client.generations.get(gen.id)
        if gen.state == "completed":
            return gen.output[0].url
        if gen.state == "failed":
            raise GenerationFailed(gen.failure_reason or "unknown")
        if time.monotonic() > deadline:
            raise GenerationTimeout(f"generation {gen.id} did not complete in {_POLL_TIMEOUT}s")
        await asyncio.sleep(_POLL_INTERVAL)


async def generate_with_anchor(instruction: str, anchor_url: str) -> str:
    """Round-N generation: produce the next image conditioned on the anchor."""
    return await generate(instruction, image_ref=[_image_ref_entry(anchor_url)])
