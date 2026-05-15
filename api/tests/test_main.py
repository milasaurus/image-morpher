from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.luma import GenerationFailed
from app.main import app
from app.models import WrittenInstruction

BASE = "http://test"


async def test_round_0_returns_two_images():
    with patch("app.main.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = ["https://cdn.luma.com/a.png", "https://cdn.luma.com/b.png"]
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
            resp = await client.post("/api/round", json={"prompt": "a vintage typewriter"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["images"] == ["https://cdn.luma.com/a.png", "https://cdn.luma.com/b.png"]
    assert body["rationale"] is None
    assert body["strategy"] is None
    assert mock_gen.call_count == 2


async def test_round_n_calls_write_instruction_with_strategy():
    choice = WrittenInstruction(rationale="B is moodier", instruction="a typewriter in moodier light")
    with patch("app.main.write_instruction", new_callable=AsyncMock, return_value=choice), \
         patch("app.main.generate", new_callable=AsyncMock, return_value="https://cdn.luma.com/new.png"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
            resp = await client.post("/api/round", json={
                "prompt": "a vintage typewriter",
                "winner_url": "https://cdn.luma.com/b.png",
                "runner_up_url": "https://cdn.luma.com/a.png",
                "strategy": "tweak",
            })

    assert resp.status_code == 200
    body = resp.json()
    assert body["images"] == ["https://cdn.luma.com/new.png"]
    assert body["rationale"] == "B is moodier"
    assert body["strategy"] == "tweak"


@pytest.mark.parametrize("strategy", ["preserve_look", "preserve_subject", "tweak"])
async def test_round_n_passes_each_strategy_to_write_instruction(strategy: str):
    choice = WrittenInstruction(rationale="B won", instruction="next prompt")
    with patch("app.main.write_instruction", new_callable=AsyncMock, return_value=choice) as mock_wi, \
         patch("app.main.generate", new_callable=AsyncMock, return_value="https://cdn.luma.com/new.png"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
            await client.post("/api/round", json={
                "prompt": "a wolf",
                "winner_url": "https://cdn.luma.com/b.png",
                "runner_up_url": "https://cdn.luma.com/a.png",
                "strategy": strategy,
            })

    _, kwargs = mock_wi.call_args
    assert kwargs.get("strategy") == strategy or mock_wi.call_args.args[3] == strategy


async def test_round_n_missing_strategy_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        resp = await client.post("/api/round", json={
            "prompt": "a wolf",
            "winner_url": "https://cdn.luma.com/b.png",
            "runner_up_url": "https://cdn.luma.com/a.png",
        })

    assert resp.status_code == 422


async def test_generation_failed_returns_502():
    with patch("app.main.generate", new_callable=AsyncMock,
               side_effect=GenerationFailed("content policy")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
            resp = await client.post("/api/round", json={"prompt": "a wolf"})

    assert resp.status_code == 502
    body = resp.json()
    assert body["error"] == "generation_failed"
    assert "content policy" in body["detail"]


async def test_round_n_generation_failed_returns_502():
    choice = WrittenInstruction(rationale="B won", instruction="next prompt")
    with patch("app.main.write_instruction", new_callable=AsyncMock, return_value=choice), \
         patch("app.main.generate", new_callable=AsyncMock,
               side_effect=GenerationFailed("timeout on anchor")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
            resp = await client.post("/api/round", json={
                "prompt": "a wolf",
                "winner_url": "https://cdn.luma.com/b.png",
                "runner_up_url": "https://cdn.luma.com/a.png",
                "strategy": "tweak",
            })

    assert resp.status_code == 502
    assert resp.json()["error"] == "generation_failed"
