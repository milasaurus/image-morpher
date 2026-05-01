# image-morpher — Build Notes

Findings worth remembering. Anything that surprised me, broke an
assumption, or would be useful to future-me.

## Open questions for the spike (Unit 1)

- [ ] **Round-0 variance.** With seeded prompts (`warm lighting` /
      `cool lighting`), do A and B differ visibly? If not, sharpen
      the seeds — the whole product depends on visible variance.
- [ ] **Channel agreement.** On 5 hand-picked obvious A/B pairs,
      does Claude pick the reference channel you'd have picked ≥3
      times? <3/5 trips the go/no-go gate.
- [ ] **`style_ref` weight.** Run the same anchor at 0.4 / 0.6 / 0.8.
      Which felt like "carry the vibe" without near-duplication?
      That number goes into `api/app/config.py` in Unit 2.
- [ ] **Cold / p50 latency.** What's a typical round take?
- [ ] **Luma URL TTL.** Do generated URLs survive ≥30 minutes idle?
      If shorter, README documents the constraint.
- [ ] **Anthropic model.** Is `claude-sonnet-4-6` still the right
      default at run time?

## Findings

(Empty — fill as I run the spike.)

## Headline finding

(Edit before shipping so the strongest finding leads.)
