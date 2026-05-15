import json
import re

from anthropic import AsyncAnthropic

from app.config import settings
from app.constants import ANTHROPIC_MAX_TOKENS
from app.models import Strategy, WrittenInstruction

_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

_SYSTEM_PROMPT = """\
You help refine image generations. The user picked image B over image A (both
generated from the same text prompt) and has chosen a strategy for the next round.

Reason briefly about why B won, then write a self-contained image-generation prompt
that embodies the chosen strategy.

Strategy definitions:
- preserve_look: keep B's visual style, mood, and lighting; allow the subject to
  vary. Write a prompt describing a NEW subject that inherits B's stylistic adjectives.
- preserve_subject: keep B's subject identity; allow scene variation. Write a prompt
  that names B's subject in a NEW context or setting.
- tweak: surgical edit on B. Write a near-copy of the original prompt with exactly
  one focused change.

The instruction is fed directly to Luma UNI-1 with image_ref pointing at the winner.
The instruction MUST be a self-contained image-generation prompt (e.g. "a vintage
typewriter on a wooden desk in moodier lighting"), NEVER a constraint description —
constraint phrasing becomes the literal UNI-1 prompt and produces garbage.

Output JSON only:
{
  "rationale": "<1-2 sentences on why B won>",
  "instruction": "<self-contained image-generation prompt for next round>"
}
"""


async def write_instruction(
    prompt: str,
    winner_url: str,
    runner_up_url: str,
    strategy: Strategy,
) -> WrittenInstruction:
    msg = await _client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=ANTHROPIC_MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Original prompt: {prompt!r}\nStrategy: {strategy}\n\nImage A (the runner-up):",
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
    return WrittenInstruction(rationale=data["rationale"], instruction=data["instruction"])
