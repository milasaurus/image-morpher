from typing import Literal

from pydantic import BaseModel, model_validator

Strategy = Literal["preserve_look", "preserve_subject", "tweak"]


class WrittenInstruction(BaseModel):
    instruction: str


class RoundRequest(BaseModel):
    prompt: str
    winner_url: str | None = None
    runner_up_url: str | None = None
    strategy: Strategy | None = None

    @model_validator(mode="after")
    def strategy_required_for_round_n(self) -> "RoundRequest":
        if self.winner_url is not None and self.strategy is None:
            raise ValueError("strategy is required when winner_url is set")
        return self


class RoundResponse(BaseModel):
    images: list[str]
    instruction: str | None = None
    strategy: Strategy | None = None


class WriteInstructionRequest(BaseModel):
    prompt: str
    winner_url: str
    strategy: Strategy
    previous_instructions: list[str] = []


class WriteInstructionResponse(BaseModel):
    instruction: str


class GenerateRequest(BaseModel):
    instruction: str
    winner_url: str
    strategy: Strategy


class GenerateResponse(BaseModel):
    image: str


class ErrorResponse(BaseModel):
    error: Literal["generation_failed", "generation_timeout", "strategy_error", "internal_error"]
    detail: str
