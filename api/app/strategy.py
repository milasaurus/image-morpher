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
Strategy definitions:
- preserve_look: borrow B's visual style, mood, lighting, and colour — but swap the
  specific subject for a different one IN THE SAME CATEGORY. Keep the subject type
  the same (person→different person, animal→different animal, object→different object
  of the same kind, building→different building). The instruction MUST open with the
  new subject, carry B's stylistic adjectives, and must NOT name B's original subject.
  The model receives image_ref pointing at B for style conditioning, so the prompt
  must clearly name the new subject to override it
  (e.g. if B showed a German Shepherd, write "a golden retriever, [B's lighting and
  mood adjectives]" — not "a cat").
- preserve_subject: study B closely and identify its subject — the specific person,
  creature, or object that is the clear focal point. Preserve that subject's identity
  exactly (appearance, details, any defining features) while placing them in a
  completely new context or setting. Write a single image generation prompt that:
  (1) names and describes the subject from B with enough detail to reproduce them
  faithfully, (2) invents a new scene, environment, or situation for them — do not
  reference or replicate B's background, (3) integrates the subject naturally into
  the new setting so it feels intentional, not transplanted.
- tweak: the user loves B and wants one focused improvement. Look at B and identify
  the single most impactful change that would make it better — examples of the kind
  of intent this captures: "the lighting is almost perfect, make it more golden",
  "great composition but add more atmospheric haze", "same scene but shift to dusk",
  "love the mood but the expression should be more intense", "add rain catching the
  neon light". Start from the original prompt and add or adjust one specific modifier.
  Keep the instruction concise — do not exhaustively re-describe B. One cohesive
  prompt, no annotation of what changed.

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
