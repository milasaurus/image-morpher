from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import WrittenInstruction
from app.strategy import write_instruction


_FAKE_B64 = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
             "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")

def _mock_response(text: str):
    msg = MagicMock()
    msg.content = [MagicMock(type="text", text=text)]
    return msg

def _patch_fetch(fn):
    """Decorator that mocks _fetch_b64 to avoid network calls."""
    async def wrapper(*args, **kwargs):
        with patch("app.strategy._fetch_b64", new=AsyncMock(return_value=(_FAKE_B64, "image/jpeg"))):
            return await fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


@_patch_fetch
async def test_write_instruction_returns_written_instruction():
    mock_resp = _mock_response(
        '{"instruction": "Change the lighting to warm golden hour. Keep everything else exactly the same."}'
    )
    with patch("app.strategy._client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_resp)
        result = await write_instruction("a vintage typewriter", "https://cdn.luma.com/winner.png", "tweak")

    assert isinstance(result, WrittenInstruction)
    assert result.instruction == "Change the lighting to warm golden hour. Keep everything else exactly the same."


@_patch_fetch
async def test_write_instruction_passes_strategy_in_user_message():
    for strategy in ("preserve_look", "preserve_subject", "tweak"):
        mock_resp = _mock_response(f'{{"instruction": "Edit instruction for {strategy}"}}')
        with patch("app.strategy._client") as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_resp)
            result = await write_instruction("a wolf howling at the moon", "https://cdn.luma.com/winner.png", strategy)

        assert result.instruction == f"Edit instruction for {strategy}"
        user_text = mock_client.messages.create.call_args.kwargs["messages"][0]["content"][0]["text"]
        assert strategy in user_text


@_patch_fetch
async def test_write_instruction_raises_on_bad_json():
    mock_resp = _mock_response("I cannot help with that.")
    with patch("app.strategy._client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_resp)
        with pytest.raises(ValueError, match="no JSON"):
            await write_instruction("a prompt", "https://cdn.luma.com/winner.png", "tweak")


@_patch_fetch
async def test_write_instruction_extracts_first_json_block():
    mock_resp = _mock_response(
        'Sure! {"instruction": "Change the lighting to dramatic side light. Keep everything else the same."}'
    )
    with patch("app.strategy._client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_resp)
        result = await write_instruction("a typewriter", "https://cdn.luma.com/winner.png", "tweak")

    assert "dramatic side light" in result.instruction
