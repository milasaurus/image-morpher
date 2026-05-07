# Progress

Last touched: 2026-05-07

## Current state

**Branch:** `spike/validate-lever-routing` (lots of commits ahead of
`planning`, no remote yet).

**Unit 1 (Spike):** rebuilt against the new Luma agents API after the
original spike surfaced a major finding — see `NOTES.md` for the
"API migration" finding. New spike code is in place; not yet run end
to end against the new API.

**Units 2–6:** not started.

## Next action

```
cd spike
uv sync       # picks up the new luma-agents dependency
uv run python spike.py
```

`LUMAAI_API_KEY` and `ANTHROPIC_API_KEY` need to be in your OS env.
The pre-flight will fail with a friendly message if either is
missing.

## Unit 1 checklist

- [ ] Run the rebuilt spike at least once end-to-end (round 0 →
      strategy pick → round 1).
- [ ] **Round-0 variance.** Bare prompt, twice. Do A and B differ
      visibly?
  - Yes → no jitter needed.
  - No → edit the round-0 `gather` in `spike/spike.py` to append
    distinct semantic modifiers (the comment block in `spike.py`
    explains the thinking).
- [ ] **Strategy agreement.** On 5 hand-picked obvious A/B pairs,
      does Claude agree with you ≥3 times? <3/5 trips the gate;
      decide before Unit 2 (sharpen system prompt / pivot README
      narrative / demote LLM step).
- [ ] **`image_ref` weight support.** Set `IMAGE_REF_WEIGHT = 0.6`
      near the top of `spike.py`. If round 1 succeeds, weight is
      supported on the new API — calibrate. If it errors, drop the
      field.
- [ ] **Latency.** Note the cold-start and p50 round timings the
      script prints.
- [ ] Log findings in `NOTES.md`.

## Decisions made since the plan was first written

These came up during the spike build. Plan + brief have been updated
to match each.

- **API migration discovered on day 0.** Luma's Dream Machine API is
  deprecated for new keys; current API is at `agents.lumalabs.ai`.
  Project pivoted from "LLM picks reference channel" to "LLM picks
  prompt strategy" — same shape of routing decision, but expressed
  in language since the new API has only one image-conditioning
  primitive (`image_ref`). See `NOTES.md` for the full finding.
- `Lever` → `RefChannel` → `Strategy` (rename history; the current
  type is `Strategy = Literal["preserve_look", "preserve_subject",
  "tweak"]`).
- `loser` renamed to `runner_up`.
- Claude default is `claude-haiku-4-5-20251001` (cheap, fast,
  vision-capable).
- API keys read from OS env. `spike/.env.example` only holds
  optional runtime knobs (WINNER, prompt overrides).
- System prompt lives in `spike/system_prompt.py` as a Python
  constant (not a `.txt` loaded via `Path.read_text`).
- Round 0 uses the bare prompt by default — no prompt jitter.
  Whether jitter is needed is one of the open questions the spike
  is meant to answer.
- Pre-flight env check at module top — friendly error message if
  required keys are missing, instead of a `KeyError` traceback.
- SDK switch from `lumaai>=1.21,<2` to `luma-agents` (different
  package, different client class `AsyncLuma`, different
  endpoint).

## Remaining units (after the spike passes the gate)

- **Unit 2** — API scaffold (`api/`) + Luma generate wrapper.
  Extracts `generate` and `generate_with_anchor` from the spike
  against the agents API.
- **Unit 3** — Pydantic models, `choose_strategy`,
  `POST /api/round`.
- **Unit 4** — React + Vite scaffold, round-0 flow.
- **Unit 5** — Round-N flow, strategy subtitle, override.
- **Unit 6** — Done flow, error states, README, ship.

## Where things live

- `docs/project-brief.md` — vision and scope (post-pivot)
- `docs/plan.md` — implementation plan (post-pivot)
- `NOTES.md` — Unit 1 open questions and findings (API migration is
  the current headline finding)
- `spike/spike.py` — the spike itself, against `agents.lumalabs.ai`
- `spike/system_prompt.py` — Claude system prompt, post-pivot to
  prompt strategies
- `spike/.env.example` / `spike/README.md` / `spike/pyproject.toml`
