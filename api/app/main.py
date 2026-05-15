import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.luma import GenerationFailed, GenerationTimeout, generate
from app.models import ErrorResponse, RoundRequest, RoundResponse
from app.strategy import write_instruction

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


def _error(kind: str, detail: str, status: int) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(error=kind, detail=detail).model_dump(),
    )


@app.post("/api/round")
async def post_round(req: RoundRequest):
    try:
        if req.winner_url is None:
            a_url, b_url = await asyncio.gather(
                generate(req.prompt),
                generate(req.prompt),
            )
            return RoundResponse(images=[a_url, b_url])

        choice = await write_instruction(
            req.prompt, req.winner_url, req.runner_up_url, req.strategy
        )
        new_b = await generate(choice.instruction, image_ref=[{"url": req.winner_url}])
        return RoundResponse(images=[new_b], rationale=choice.rationale, instruction=choice.instruction, strategy=req.strategy)

    except (GenerationFailed, GenerationTimeout) as exc:
        kind = "generation_failed" if isinstance(exc, GenerationFailed) else "generation_timeout"
        return _error(kind, str(exc), 502)
    except ValueError as exc:
        return _error("strategy_error", str(exc), 502)
    except Exception as exc:
        return _error("internal_error", str(exc), 502)
