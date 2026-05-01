# image-morpher — Build Notes

Findings worth remembering. Anything that surprised me, broke an
assumption, or would be useful to future-me 

## Open questions to validate

- [ ] Does Photon return two different images when called twice with
      the identical prompt? If outputs are near-duplicates, round 0
      needs prompt jitter — the whole product depends on visible
      variance between A and B.
- [ ] What does `weight` *feel* like across the 0–1 range on
      `image_ref` and `style_ref`? Where's the line between "carry
      the vibe" and "near-duplicate"?
- [ ] Is `modify_image_ref` materially different from a fresh
      generation with the winner as a high-weight `image_ref`? Or
      are they the same thing under the hood?
- [ ] Latency: p50 / p99 across `photon-1` vs `photon-flash-1`. Is
      flash good enough for the rapid pick-pick-pick rhythm?
- [ ] Does the LLM lever-selection produce sensible JSON
      consistently? Failure modes? When does the lever choice feel
      obviously wrong?

## Findings

(Empty — fill as I build.)
