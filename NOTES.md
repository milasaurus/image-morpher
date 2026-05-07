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

## Findings

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
