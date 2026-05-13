from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.luma import (
    GenerationFailed,
    GenerationTimeout,
    generate,
    generate_with_anchor,
)


def _gen(state: str, url: str = "https://cdn.luma.com/img.png", failure_reason: str | None = None):
    g = MagicMock()
    g.id = "gen-123"
    g.state = state
    g.output = [MagicMock(url=url)]
    g.failure_reason = failure_reason
    return g


async def test_generate_happy_path():
    queued = _gen("queued")
    completed = _gen("completed", url="https://cdn.luma.com/result.png")

    with patch("app.luma._client") as mock_client, \
         patch("app.luma.asyncio.sleep", new_callable=AsyncMock):
        mock_client.generations.create = AsyncMock(return_value=queued)
        mock_client.generations.get = AsyncMock(side_effect=[queued, completed])

        url = await generate("a vintage typewriter on a wooden desk")

    assert url == "https://cdn.luma.com/result.png"
    mock_client.generations.create.assert_called_once()
    call_kwargs = mock_client.generations.create.call_args.kwargs
    assert call_kwargs["prompt"] == "a vintage typewriter on a wooden desk"
    assert call_kwargs["model"] == "uni-1"
    assert call_kwargs["type"] == "image"
    assert call_kwargs["output_format"] == "png"
    assert "image_ref" not in call_kwargs


async def test_generate_passes_image_ref():
    completed = _gen("completed", url="https://cdn.luma.com/anchored.png")

    with patch("app.luma._client") as mock_client, \
         patch("app.luma.asyncio.sleep", new_callable=AsyncMock):
        mock_client.generations.create = AsyncMock(return_value=completed)
        mock_client.generations.get = AsyncMock(return_value=completed)

        await generate("a prompt", image_ref=[{"url": "https://cdn.luma.com/winner.png"}])

    call_kwargs = mock_client.generations.create.call_args.kwargs
    assert call_kwargs["image_ref"] == [{"url": "https://cdn.luma.com/winner.png"}]


async def test_generate_raises_on_failure():
    queued = _gen("queued")
    failed = _gen("failed", failure_reason="content policy violation")

    with patch("app.luma._client") as mock_client, \
         patch("app.luma.asyncio.sleep", new_callable=AsyncMock):
        mock_client.generations.create = AsyncMock(return_value=queued)
        mock_client.generations.get = AsyncMock(side_effect=[queued, failed])

        with pytest.raises(GenerationFailed, match="content policy violation"):
            await generate("some prompt")


async def test_generate_raises_on_failure_unknown_reason():
    failed = _gen("failed", failure_reason=None)

    with patch("app.luma._client") as mock_client, \
         patch("app.luma.asyncio.sleep", new_callable=AsyncMock):
        mock_client.generations.create = AsyncMock(return_value=failed)
        mock_client.generations.get = AsyncMock(return_value=failed)

        with pytest.raises(GenerationFailed, match="unknown"):
            await generate("some prompt")


async def test_generate_raises_on_timeout():
    queued = _gen("queued")

    with patch("app.luma._client") as mock_client, \
         patch("app.luma.asyncio.sleep", new_callable=AsyncMock), \
         patch("app.luma.time") as mock_time:
        mock_client.generations.create = AsyncMock(return_value=queued)
        mock_client.generations.get = AsyncMock(return_value=queued)
        # First call sets the deadline (0.0 + 180.0 = 180.0).
        # Second call checks it (181.0 > 180.0 → timeout).
        mock_time.monotonic.side_effect = [0.0, 181.0]

        with pytest.raises(GenerationTimeout):
            await generate("some prompt")


async def test_generate_with_anchor_passes_image_ref():
    completed = _gen("completed", url="https://cdn.luma.com/anchored.png")

    with patch("app.luma._client") as mock_client, \
         patch("app.luma.asyncio.sleep", new_callable=AsyncMock):
        mock_client.generations.create = AsyncMock(return_value=completed)
        mock_client.generations.get = AsyncMock(return_value=completed)

        url = await generate_with_anchor(
            "a leather journal in warm light",
            "https://cdn.luma.com/winner.png",
        )

    assert url == "https://cdn.luma.com/anchored.png"
    call_kwargs = mock_client.generations.create.call_args.kwargs
    assert call_kwargs["image_ref"] == [{"url": "https://cdn.luma.com/winner.png"}]
    assert call_kwargs["prompt"] == "a leather journal in warm light"
