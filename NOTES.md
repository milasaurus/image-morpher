# Notes

Findings from building image-morpher.

---

## "Same look, new subject" remains the hardest strategy

**The simple version:** "Refine this" and "New scene, same subject" both work by editing the winning image directly — the model sees the pixels and applies a specific change. "New subject, same look" is different: you want the visual style to survive but the subject to be replaced entirely. That's a harder instruction for the model to follow because style and subject are entangled in the same pixels.

**The technical version:** We now use `type: "image_edit"` with the winner as `source` for all three strategies. For `tweak` and `preserve_subject`, this works well — the edit model preserves style from pixels while applying a targeted change. For `preserve_look`, the instruction says "replace the subject, keep the lighting/mood" — but because subject and style are encoded together in the source, the model often keeps both.

The original Dream Machine API exposed a dedicated `style_ref` channel that conditioned on style only, leaving subject identity free. The agents API (confirmed 2026-05-15) has no equivalent — its full parameter surface is: `prompt`, `model`, `aspect_ratio`, `style` (presets: `auto`/`manga` only), `output_format`, `web_search`, `image_ref`, and `source` (for edits). A `style_ref` primitive would make `preserve_look` reliable: pass the winner for style conditioning and a prompt naming the new subject, and the model has both signals unambiguously. Without it, the strategy is best-effort.

**Potential lever — `web_search: true`:** for `preserve_look`, Claude could name a specific visual style (e.g. "Blade Runner 2049 colour grading") in the instruction and `web_search: true` might help the model source that look from external references rather than the source image. Untested.

---

## LLM cannot reliably infer user intent from an image pick alone

Even a vision-capable model (Claude Haiku 4.5) can correctly identify *why* B beat A — better mood, tighter composition, more dramatic lighting — but cannot determine *what the user wants next* from that signal alone. Picking B over A could mean "I want this exact feeling extended" or "I want this subject in a different scene" or "tweak this one thing." The LLM has no way to disambiguate.

This killed the original design (LLM picks the strategy). Two gate cases confirmed it: the typewriter prompt returned the wrong strategy label despite writing a correct instruction; the wolf-howling-at-moon case replaced the wolf with an eagle when `tweak` was the natural call.

**Fix:** strategy moved to explicit user input. The three-button picker ("Refine this / New subject, same look / New scene, same subject") replaced the routing decision entirely. LLM kept the prompt-authoring role — that part worked well throughout.

---

## UNI-1 latency is 30–60 s per generation, not 10–20 s

Round 0 (two parallel calls): ~47 s. Round N (one serial call with `image_ref`): ~62 s. An 8–10 round session is 10–15 minutes of waiting. The design goal of "latency feels like part of the craft" is at risk on longer sessions.

`preserve_look` via `image_edit` hit 180 s timeouts in testing — longer than the other strategies, likely because replacing a subject while preserving style is a harder edit for the model. `POLL_TIMEOUT_S` was bumped from 180 to 300 to accommodate this.

---

## Each generation costs ~60 s — wrong guesses are expensive

At 30–60 s per generation, a misfire isn't just annoying — it's the dominant cost of using the tool. The current flow commits to a Luma generation the moment a strategy is clicked, with no checkpoint in between. If Claude writes an instruction the user wouldn't have chosen, they only find out a minute later.

The fix is a prompt-review step: after the user picks a strategy, call Claude to get the instruction, then surface it in an editable field *before* triggering Luma. The user can read, adjust, and confirm — one lightweight step that can eliminate the most expensive mistakes.

This is the clearest v2 improvement: split `/api/round` into two steps — `write_instruction` (fast, cheap) and `generate` (slow, expensive) — with a human checkpoint in the middle.

Showing the Claude-written prompt during the Luma wait also meaningfully reduces *perceived* latency. The user has something concrete to read and react to while the image generates, which makes the 60–90s feel purposeful rather than empty.

---

## UNI-1 produces near-identical images from the same prompt

Round 0 generates A and B from the identical prompt with no jitter. In practice, the two images come back looking nearly the same — UNI-1 has little visible non-determinism on repeated calls. This undermines the A/B premise: if A and B look identical, the user has nothing meaningful to pick between.

---

## Claude defaults to the original prompt's scene when generating new scenes

When asked to place a subject in a "completely new scene," Claude kept reverting to settings pulled directly from the original user prompt — even when the user had already moved through several different scenes. The original prompt is always present in the request context, and when it's long and visually specific, Claude treats that description as a strong prior and gravitates back to it, especially on later rounds when the instruction history is thin.

The fix was blunt: explicitly tell Claude in every request not to reuse scenes or environments from the original prompt. It worked, but it's a prompt-level patch over a model behaviour — Claude doesn't inherently understand "you already showed the user this; try something different." Session history helps (we now pass all previous instructions), but the original prompt anchor is persistent enough that you have to call it out directly.

---

## `image_ref` weight field — not yet probed

The agents API docs only list `url` / `data` / `media_type` on `image_ref` entries. The old Dream Machine API had a `weight` field. We never confirmed whether the new API accepts it. `IMAGE_REF_WEIGHT` is left `None` in config; conditioning strength is prompt-only for now.
