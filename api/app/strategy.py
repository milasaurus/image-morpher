import json
import re

from anthropic import AsyncAnthropic

from app.config import settings
from app.constants import ANTHROPIC_MAX_TOKENS
from app.models import Strategy, WrittenInstruction

_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

_SYSTEM_PROMPT = """\
You write image edit instructions for Luma UNI-1. The user picked image B over image A.
B will be passed as the source image for editing — UNI-1 preserves everything you do
not mention, so be specific about what to change and explicit about what to keep.

Output a single JSON object:

{
  "rationale": "<1-2 sentences on why B won>",
  "instruction": "<edit directive for UNI-1>"
}

Strategy rules:

preserve_look — swap the subject for a different one IN THE SAME CATEGORY
  (person→different person, animal→same-type animal, object→same-type object).
  Keep B's lighting, colour palette, mood, atmosphere, and composition exactly.
  Instruction format: "Replace [B's subject] with [new subject of same category].
  Keep the lighting, colour palette, mood, atmosphere, and composition identical."
  Name the new subject specifically. Name what to keep specifically.

preserve_subject — keep B's subject exactly (appearance, identifying features,
  expression, clothing). Replace the background and setting with a new scene.
  Instruction format: "Replace the background and setting with [new environment].
  Keep [subject description] exactly as they appear — same pose, expression,
  and appearance."

tweak — make exactly one focused improvement. Identify the single most impactful
  change: lighting temperature, time of day, weather, one added element, colour
  grade, expression, or mood shift. Keep everything else identical.
  Instruction format: "Change [specific element] to [new version].
  Keep everything else exactly the same."
  Be surgical. One change only.
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
