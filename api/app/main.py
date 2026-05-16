import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.luma import GenerationFailed, GenerationTimeout, edit, generate
from app.models import (
    ErrorResponse,
    GenerateRequest,
    GenerateResponse,
    RoundRequest,
    RoundResponse,
    WriteInstructionRequest,
    WriteInstructionResponse,
)
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


@app.post("/api/write-instruction")
async def post_write_instruction(req: WriteInstructionRequest):
    try:
        choice = await write_instruction(
            req.prompt, req.winner_url, req.strategy
        )
        return WriteInstructionResponse(instruction=choice.instruction, rationale=choice.rationale)
    except ValueError as exc:
        return _error("strategy_error", str(exc), 502)
    except Exception as exc:
        return _error("internal_error", str(exc), 502)


@app.post("/api/generate")
async def post_generate(req: GenerateRequest):
    try:
        if req.strategy == "tweak":
            url = await edit(req.winner_url, req.instruction)
        elif req.strategy == "preserve_subject":
            url = await generate(req.instruction, image_ref=[{"url": req.winner_url}])
        else:  # preserve_look
            url = await generate(req.instruction)
        return GenerateResponse(image=url)
    except (GenerationFailed, GenerationTimeout) as exc:
        kind = "generation_failed" if isinstance(exc, GenerationFailed) else "generation_timeout"
        return _error(kind, str(exc), 502)
    except Exception as exc:
        return _error("internal_error", str(exc), 502)


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
            req.prompt, req.winner_url, req.strategy
        )
        if req.strategy == "tweak":
            new_b = await edit(req.winner_url, choice.instruction)
        elif req.strategy == "preserve_subject":
            new_b = await generate(choice.instruction, image_ref=[{"url": req.winner_url}])
        else:  # preserve_look
            new_b = await generate(choice.instruction)
        return RoundResponse(images=[new_b], rationale=choice.rationale, instruction=choice.instruction, strategy=req.strategy)

    except (GenerationFailed, GenerationTimeout) as exc:
        kind = "generation_failed" if isinstance(exc, GenerationFailed) else "generation_timeout"
        return _error(kind, str(exc), 502)
    except ValueError as exc:
        return _error("strategy_error", str(exc), 502)
    except Exception as exc:
        return _error("internal_error", str(exc), 502)
