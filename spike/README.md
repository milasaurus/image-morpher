# spike

Single-file Python spike. Validates the round-0 → lever → round-1
loop end-to-end before any backend code. See `docs/plan.md` Unit 1
for the rationale and the go/no-go gate.

## Run

```
cd spike
cp .env.example .env  # add LUMAAI_API_KEY (Anthropic is read from OS env)
uv sync
uv run python spike.py
```

By default the script assumes B is the winner. After the round-0
URLs print, open both in a browser; if you'd actually pick A, set
`WINNER=A` in `.env` and re-run.

## What to do with it

The spike is the apparatus, not the experiment. Run it multiple
times to gather the data Unit 1 wants in `NOTES.md`:

- **Round-0 variance.** With the seeded prompts, do A and B differ
  visibly? If not, sharpen the seeds.
- **Lever agreement (≥3/5 = go).** Pick 5 prompts where the right
  lever feels obvious to you. Run, eyeball Claude's pick, tally
  agreement. <3/5 means sharpen the prompt, pivot the README
  narrative ("why this is harder than it looks"), or demote the
  LLM step.
- **`style_ref` weight.** Re-run with `WEIGHT_STYLE_REF=0.4` /
  `0.6` / `0.8`. Pick whichever felt like "carry the vibe" without
  near-duplication. That value goes into the backend's
  `config.py` in Unit 2.
- **Latency.** Note the cold and p50 round timings the script
  prints.
- **Luma URL TTL.** Open one of the printed URLs, leave the tab
  idle 30+ minutes, refresh. Still works?

Log findings as you go in `../NOTES.md`.
