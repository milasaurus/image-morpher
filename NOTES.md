# image-morpher — Build Notes

Findings worth remembering. Anything that surprised me, broke an
assumption, or would be useful to future-me.

## Open questions for the spike (Unit 1)

- [ ] **Round-0 variance / jitter need.** Run with the bare prompt.
      Do A and B differ visibly on their own? If yes, no jitter
      needed. If not, edit `spike.py` to append distinct semantic
      modifiers (e.g. `, warm lighting` / `, cool lighting`) — note
      that the jitter axis frames what dimension A vs B is asking.
- [ ] **Strategy agreement.** On 5 hand-picked obvious A/B pairs,
      does Claude pick the strategy you'd have picked ≥3 times?
      <3/5 trips the go/no-go gate.
- [ ] **`image_ref` weight support.** Does the new agents API accept
      a `weight` field on `image_ref` entries? If yes, what value
      feels like "carry the vibe" without near-duplication? If no,
      conditioning is prompt-only.
- [ ] **Cold / p50 latency.** What's a typical round take?

## Strategy gate progress (≥3/5 = go)

| # | Prompt | Claude's pick | What I'd have picked | Match? |
|---|--------|---------------|----------------------|--------|
| 1 | "a vintage typewriter on a wooden desk" | `preserve_subject` | `preserve_look` (A vs B differ in composition / DOF / lighting, not subject) | **miss** |
| 2 | TBD | | | |
| 3 | TBD | | | |
| 4 | TBD | | | |
| 5 | TBD | | | |

## Findings

### Latency: UNI-1 generations take 30–60s, not 10–20s (logged 2026-05-07)

First spike run timings:

- Round 0 (two parallel `generate(prompt)` calls): **47.8s**
- Round 1 (one serial `generate_with_anchor` call): **62.5s**

Each generation is roughly 30–60s on this account, well above the
10–20s the plan assumed. Implications:

- An 8–15 round session is **4–15 minutes of waiting** at this rate.
- The plan's `POLL_TIMEOUT = 180s` is sufficient (each gen finishes
  inside it), but we're closer to the edge than expected.
- The design's "per-round latency feels like part of the craft, not
  a wait" target (R10) is at risk. A single late round in a 12-pick
  session could push the user past their attention budget.
- Speculative pre-generation of round N+1 (currently parked as v2)
  becomes more attractive: a quietly-running pre-fetch could mask a
  large fraction of perceived latency.

Need more data points before treating this as the headline. Re-run
the spike a few times to get a real cold/p50 distribution.

### Strategy mislabel — instruction is right, label is wrong (case 1, logged 2026-05-07)

Case 1 of the gate (vintage typewriter prompt). Claude chose
`preserve_subject`, but its own rationale described *look*
attributes:

> "tighter, more intimate close-up perspective… angled viewpoint and
> shallow depth of field create better visual drama"

The subject was identical in A and B (typewriter on desk); what
differed was lighting, depth of field, perspective — i.e. *look*.
A `preserve_look` strategy was the honest call.

Notably, the *instruction* Claude wrote was a perfectly reasonable
preserve-look prompt:

> "a vintage typewriter on a wooden desk, captured with a close-up
> angled perspective emphasizing mechanical details and texture,
> golden hour warm lighting, shallow depth of field with blurred
> background"

Decision 4 held — instruction is self-contained, no constraint
phrasing. The strategy field is the unreliable part, not the prompt
authoring.

**Emerging pattern (only 1/5 so far, but worth watching):** Claude
may be writing the right prompt but tagging it with whichever
strategy label sounds adjacent. If this repeats across cases 2–5,
the strategy field is mostly noise — the LLM's actual job is prompt
authoring, and the routing-by-label premise weakens. Could pivot to
just `{rationale, instruction}` and use the strategy concept only
for the override dropdown.

### API migration: Dream Machine → agents API (logged 2026-05-07)

The plan (and its first spike scaffold) targeted the older Dream
Machine API at `api.lumalabs.ai/dream-machine/...` via the `lumaai`
Python SDK, with three distinct reference channels (`style_ref`,
`character_ref`, `modify_image_ref`). On first run, the spike got
`403 Not authenticated` — the key worked at
`agents.lumalabs.ai/v1/generations` (uni-1) but not at the legacy
endpoint.

Verified the migration: the current Luma agents API exposes a single
`image_ref` primitive. The three-channel routing concept doesn't
exist on this surface; UNI-1 is meant to interpret the reference's
role from natural-language prompts.

The project pivoted from "LLM picks the right reference channel" to
"LLM picks the right *prompt strategy* (preserve_look /
preserve_subject / tweak) and writes a strategy-flavoured prompt."
Brief and plan rewritten to match. The spike was rebuilt against
`luma-agents` SDK + `uni-1` model.

**Why this is the headline finding:** the spike did its job on day 0.
A weekend invested against a deprecated API surface would have been
discovered far later, at greater cost, and we'd have been weeks into
backend work before realizing the routing premise didn't even apply
to the available API.

(More findings will land here as the rebuilt spike runs.)

## Headline finding

(Edit before shipping so the strongest finding leads. The API-migration
finding above is the current headline candidate.)
