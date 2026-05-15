# Notes

Findings from building image-morpher. Strongest first.

---

## LLM cannot reliably infer user intent from an image pick alone

Even a vision-capable model (Claude Haiku 4.5) can correctly identify *why* B beat A — better mood, tighter composition, more dramatic lighting — but cannot determine *what the user wants next* from that signal alone. Picking B over A could mean "I want this exact feeling extended" or "I want this subject in a different scene" or "tweak this one thing." The LLM has no way to disambiguate.

This killed the original design (LLM picks the strategy). Two gate cases confirmed it: the typewriter prompt returned the wrong strategy label despite writing a correct instruction; the wolf-howling-at-moon case replaced the wolf with an eagle when `tweak` was the natural call.

**Fix:** strategy moved to explicit user input. The three-button picker ("Refine this / New subject, same look / New scene, same subject") replaced the routing decision entirely. LLM kept the prompt-authoring role — that part worked well throughout.

---

## UNI-1 latency is 30–60 s per generation, not 10–20 s

Round 0 (two parallel calls): ~47 s. Round N (one serial call with `image_ref`): ~62 s. An 8–10 round session is 10–15 minutes of waiting. The design goal of "latency feels like part of the craft" is at risk on longer sessions.

Mitigation shipped: skeleton shimmer + elapsed-second counter. Speculative pre-generation of round N+1 would mask most of the perceived wait and is the obvious v2 improvement.

---

## Instruction quality is solid; the strategy label was the only failure mode

Even in cases where the model mis-labelled the strategy, the written `instruction` was usable — it described the right visual qualities for the next generation. The prompt-authoring role is mechanically reliable. The failure was upstream (routing), not in the writing.

---

## Each generation costs ~60 s — wrong guesses are expensive

At 30–60 s per generation, a misfire isn't just annoying — it's the dominant cost of using the tool. The current flow commits to a Luma generation the moment a strategy is clicked, with no checkpoint in between. If Claude writes an instruction the user wouldn't have chosen, they only find out a minute later.

The fix is a prompt-review step: after the user picks a strategy, call Claude to get the instruction, then surface it in an editable field *before* triggering Luma. The user can read, adjust, and confirm — one lightweight step that can eliminate the most expensive mistakes. This also returns control to the user for cases where the LLM writes a reasonable but subtly wrong prompt (e.g. changes the subject when the user wanted to preserve it).

This is the clearest v2 improvement: split `/api/round` into two steps — `write_instruction` (fast, cheap) and `generate` (slow, expensive) — with a human checkpoint in the middle.

---

## UNI-1 produces near-identical images from the same prompt

Round 0 generates A and B from the identical prompt with no jitter. In practice, the two images come back looking nearly the same — UNI-1 has little visible non-determinism on repeated calls. This undermines the A/B premise: if A and B look identical, the user has nothing meaningful to pick between.

The fix is prompt jitter — append distinct semantic modifiers to each call at round 0 (e.g. `, warm golden-hour lighting` vs `, cool overcast lighting`). The axis you choose frames what dimension the A/B choice is actually asking about, so it should be picked deliberately rather than defaulting to a neutral nonce. This is the most important unresolved issue for the round-0 experience.

---

## `image_ref` weight field — not yet probed

The agents API docs only list `url` / `data` / `media_type` on `image_ref` entries. The old Dream Machine API had a `weight` field. We never confirmed whether the new API accepts it. `IMAGE_REF_WEIGHT` is left `None` in config; conditioning strength is prompt-only for now.

---

## Luma URL TTL is ~1 hour

Presigned S3 URLs carry `X-Amz-Expires=3600`. No backend proxy needed within a session. Documented in the README.

---

## API migration finding (from spike setup)

The original spike targeted the `lumaai` SDK (`lumaai>=1.21`). The agents API is a different package (`luma-agents`), different client class (`AsyncLuma`), and different base URL (`agents.lumalabs.ai`). The generation surface is: `luma.generations.create(**kwargs)` → poll `luma.generations.get(id)` until `state == "completed"` → URL at `output[0].url`.
