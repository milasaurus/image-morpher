import asyncio
import base64
import io
import json
import re
import urllib.request

from PIL import Image

from anthropic import AsyncAnthropic

from app.config import settings
from app.constants import ANTHROPIC_MAX_TOKENS
from app.models import Strategy, WrittenInstruction

_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


_MAX_SIDE = 1024
_JPEG_QUALITY = 85
_MAX_B64_BYTES = 4_800_000  # stay well under Anthropic's 5 MB limit


async def _fetch_b64(url: str) -> tuple[str, str]:
    """Download, resize if needed, and return (base64_jpeg, 'image/jpeg')."""
    def _fetch():
        with urllib.request.urlopen(url, timeout=30) as r:
            raw = r.read()
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        if max(img.size) > _MAX_SIDE:
            img.thumbnail((_MAX_SIDE, _MAX_SIDE), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
        return base64.standard_b64encode(buf.getvalue()).decode(), "image/jpeg"
    return await asyncio.get_running_loop().run_in_executor(None, _fetch)

_SYSTEM_PROMPT = """\
You write image edit instructions for Luma UNI-1. The user picked image B over image A.
B will be passed as the source image for editing — UNI-1 preserves everything you do
not mention, so be specific about what to change and explicit about what to keep.

Output a single JSON object:

{
  "instruction": "<edit directive for UNI-1>"
}

Strategy rules:

preserve_look — replace B's subject with a different one of the same category
  (person→person, animal→animal, object→object). The new subject must create
  visual contrast through an unexpected dimension — NOT just age or gender.
  Think: different archetype entirely (a performer, a child, a warrior, a monk,
  a machine-human hybrid, an athlete); a radically different cultural or
  historical identity; an entirely different body type or silhouette; someone
  whose presence in this aesthetic feels surprising. Do not default to
  "elderly person" as the contrast — push further.
  Keep B's lighting, colour palette, mood, atmosphere, and composition exactly.
  Instruction format: "Replace [B's subject described briefly] with [specific,
  unexpected new subject]. Keep the lighting, colour palette, mood, atmosphere,
  and composition identical."

preserve_subject — composite operation: keep the foreground subject exactly as
  they appear in the source image and replace the entire background with a new
  scene. The subject's appearance, position, and expression must be pixel-perfect
  from the source — do not alter them. Only the environment behind them changes.
  The new scene must stay within the same aesthetic genre as the original — if
  it's cyberpunk, find a different cyberpunk location; if it's nature, find a
  different natural environment; if it's urban, find a different city setting.
  Change the specific place, not the overall world.
  Instruction format: "Keep [subject name/description] exactly as shown in the
  source image. Replace the entire background and surrounding environment with
  [specific new scene within the same aesthetic: different location, time of day,
  lighting, atmosphere]. Nothing from the original background should remain."
  The new scene must be specific — name the location, lighting quality, and mood.

tweak — improve the image by adding visual interest or changing what's happening.
  Do NOT adjust contrast, saturation, brightness, or colour grade — those are
  technical parameters, not improvements. Instead, identify one of these:
  (1) add something interesting to the background or environment — a detail,
      an element, or activity that enriches the scene without changing the subject;
  (2) change what the subject is doing — their action, gesture, or expression;
  (3) add an environmental element that creates more narrative or atmosphere
      (steam, rain, additional characters in the distance, light source, etc.)
  Instruction format: "Change [what the subject is doing / add X to the background].
  Keep everything else exactly the same."
"""


async def write_instruction(
    prompt: str,
    winner_url: str,
    strategy: Strategy,
    previous_instructions: list[str] | None = None,
) -> WrittenInstruction:
    winner_b64, winner_mime = await _fetch_b64(winner_url)

    history = (
        "\n\nDo NOT reuse scenes, settings, or environments from the original "
        "prompt — the user wants something new."
    )
    if previous_instructions:
        lines = "\n".join(f"  - {i}" for i in previous_instructions)
        history += (
            f"\n\nPreviously generated instructions this session — generate "
            f"something meaningfully different from all of these:\n{lines}"
        )

    msg = await _client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=ANTHROPIC_MAX_TOKENS,
        temperature=1.0,
        system=[
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Original prompt: {prompt!r}\nStrategy: {strategy}{history}\n\nImage B (the winner):",
                    },
                    {"type": "image", "source": {"type": "base64", "media_type": winner_mime, "data": winner_b64}},
                ],
            }
        ],
    )
    text = "".join(block.text for block in msg.content if block.type == "text")
    m = _JSON_RE.search(text)
    if not m:
        raise ValueError(f"no JSON in LLM response: {text!r}")
    data = json.loads(m.group(0))
    return WrittenInstruction(instruction=data["instruction"])
