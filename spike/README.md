# spike

Single-file Python spike. Validates the round-0 → reference channel →
round-1 loop end-to-end before any backend code. See `docs/plan.md`
Unit 1 for the rationale and the go/no-go gate.

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
  axis you pick frames what dimension A vs B is asking the user to
  vote on, so it's a deliberate edit, not a config knob.
- **Reference-channel agreement (≥3/5 = go).** Pick 5 prompts where
  the right channel feels obvious to you. Run, eyeball Claude's
  pick, tally agreement. <3/5 means sharpen the prompt, pivot the
  README narrative ("why this is harder than it looks"), or demote
  the LLM step.
- **`style_ref` weight.** Re-run with `WEIGHT_STYLE_REF=0.4` /
  `0.6` / `0.8`. Pick whichever felt like "carry the vibe" without
  near-duplication. That value goes into the backend's `config.py`
  in Unit 2.
- **Latency.** Note the cold and p50 round timings the script
  prints.
- **Luma URL TTL.** Open one of the printed URLs, leave the tab
  idle 30+ minutes, refresh. Still works?

Log findings as you go in `../NOTES.md`.
