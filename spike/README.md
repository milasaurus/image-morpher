# spike

Single-file Python spike. Validates the round-0 → strategy → round-1
loop end-to-end before any backend code. See `docs/plan.md` Unit 1
for the rationale and the go/no-go gate.

## Run

```
cd spike
uv sync
uv run python spike.py
```

`LUMAAI_API_KEY` and `ANTHROPIC_API_KEY` are read from the OS env.

The default winner is B. After the round-0 URLs print, open both in a
browser; if you'd actually pick A, copy `.env.example` to `.env`,
uncomment `WINNER=A`, and re-run.

## What to do with it

The spike is the apparatus, not the experiment. Run it multiple
times to gather the data Unit 1 wants in `NOTES.md`:

- **Round-0 variance / jitter need.** Run with the bare prompt
  (default — no jitter). Do A and B differ visibly on their own?
  If yes, no prompt jitter needed. If they come back near-identical,
  edit `spike.py` to append distinct semantic modifiers to each
  call (e.g. `, warm lighting` vs `, cool lighting`). The jitter
  axis frames what dimension A vs B is asking the user to vote on,
  so it's a deliberate edit, not a config knob.
- **Strategy agreement (≥3/5 = go).** Pick 5 prompts where the right
  strategy feels obvious to you. Run, eyeball Claude's pick, tally
  agreement. <3/5 means sharpen the system prompt, pivot the README
  narrative ("why this is harder than it looks"), or demote the
  LLM step.
- **`image_ref` weight support.** Set `IMAGE_REF_WEIGHT = 0.6` near
  the top of `spike.py` and re-run. If round 1 succeeds, the new
  agents API accepts weight on entries — calibrate at 0.4 / 0.6 /
  0.8 and pick whichever felt like "carry the vibe". If the request
  errors with 400/422, weight isn't supported — drop it and rely on
  prompt-only conditioning.
- **Latency.** Note the cold and p50 round timings the script
  prints.

Log findings as you go in `../NOTES.md`.
