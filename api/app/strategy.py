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

preserve_subject — describe B's subject in precise detail (appearance, identifying
  features, expression, clothing, pose) so UNI-1 can reproduce them faithfully.
  Then invent a completely new scene. This strategy uses image_ref for subject
  conditioning and generates fresh — write it as a self-contained generation
  prompt, not an edit directive. Instruction format:
  "[Subject description with identifying details], [new scene: location, time
  of day, lighting, atmosphere, composition]."
  The scene must be specific and concrete — name a real location or environment,
  lighting quality, and mood. Nothing from B's original background should appear.

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
    strategy: Strategy,
) -> WrittenInstruction:
    winner_b64, winner_mime = await _fetch_b64(winner_url)

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
                        "text": f"Original prompt: {prompt!r}\nStrategy: {strategy}\n\nImage B (the winner):",
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
    return WrittenInstruction(rationale=data["rationale"], instruction=data["instruction"])
