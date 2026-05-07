# Progress

Last touched: 2026-05-07

## Current state

**Branch:** `spike/validate-lever-routing` (13 commits ahead of
`planning`, no remote yet).

**Unit 1 (Spike):** scaffolded, not yet run. Code in `spike/` is
ready; awaiting first execution + the go/no-go gate.

**Units 2–6:** not started.

## Next action

```
cd spike
uv sync
uv run python spike.py
```

`LUMAAI_API_KEY` and `ANTHROPIC_API_KEY` need to be in your OS env.
The spike pre-flight will fail with a friendly message if either is
missing.

## Unit 1 checklist

- [ ] Run the spike at least once end-to-end (round 0 → channel
      pick → round 1).
- [ ] **Round-0 variance.** Bare prompt, twice. Do A and B differ
      visibly?
  - Yes → no jitter needed.
  - No → edit the round-0 `gather` in `spike/spike.py` to append
    distinct semantic modifiers (the comment near `WEIGHT_STYLE_REF`
    explains the thinking).
- [ ] **Channel agreement.** On 5 hand-picked obvious A/B pairs,
      does Claude agree with you ≥3 times? <3/5 trips the gate;
      decide before Unit 2 (sharpen prompt / pivot README narrative /
      demote LLM step).
- [ ] **`style_ref` weight.** Re-run with `WEIGHT_STYLE_REF=0.4` /
      `0.6` / `0.8`. Pick whichever felt like "carry the vibe"
      without near-duplication. That value goes into `api/app/config.py`
      in Unit 2.
- [ ] **Latency.** Note the cold-start and p50 round timings the
      script prints.
- [ ] **Luma URL TTL.** Open one of the printed URLs, leave it idle
      30+ min, refresh. Still works?
- [ ] Log findings in `NOTES.md`.

## Decisions made since the plan was written

The plan + brief have been updated to match these.

- `Lever` renamed to `RefChannel` (type alias, JSON field name, file
  paths, all prose).
- `loser` renamed to `runner_up`.
- Claude default is `claude-haiku-4-5-20251001` (cheap, fast,
  vision-capable). Sonnet is a viable upgrade if Haiku looks shaky.
- API keys read from OS env. `spike/.env.example` only holds
  optional runtime knobs (WINNER, prompt, weights).
- System prompt lives in `spike/system_prompt.py` as a Python
  constant (not a `.txt` loaded via `Path.read_text`).
- Round 0 uses the bare prompt by default — no prompt jitter.
  Whether jitter is needed is one of the open questions the spike
  is meant to answer.
- Anthropic key is read from OS env (no `.env` entry needed).
- Pre-flight env check at module top — friendly error message if
  required keys are missing, instead of a `KeyError` traceback.

## Remaining units (after the spike passes the gate)

- **Unit 2** — API scaffold (`api/`) + Luma generate wrapper.
  Extracts `generate` and `generate_with_ref_channel` from the spike.
- **Unit 3** — Pydantic models, `choose_ref_channel`,
  `POST /api/round`.
- **Unit 4** — React + Vite scaffold, round-0 flow.
- **Unit 5** — Round-N flow, ref-channel subtitle, override.
- **Unit 6** — Done flow, error states, README, ship.

## Where things live

- `docs/project-brief.md` — vision and scope
- `docs/plan.md` — implementation plan
- `NOTES.md` — Unit 1 open questions and findings (currently empty)
- `spike/spike.py` — the spike itself
- `spike/system_prompt.py` — Claude system prompt
- `spike/.env.example` / `spike/README.md` / `spike/pyproject.toml`
