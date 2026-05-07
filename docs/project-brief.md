# image-morpher — Project Brief

## What this is

image-morpher is an A/B image refinement loop built on Luma's API.

You describe an image in words. You get two versions. You pick the one
you like more. That winner stays on screen as your anchor — the new "A" —
and a new candidate "B" is generated alongside it, refined in the
direction of what you liked. You keep picking until you're happy, then
export.

The interesting part is what happens between rounds: an LLM looks at
both images, reasons about why you picked the winner, and decides what
*shape* of prompt to write next — one that preserves B's look, B's
subject, or tweaks B surgically. You can override its choice. Each
round the search space narrows. You're doing gradient descent on an
image, with yourself as the loss function.

Built on Luma's agents API (UNI-1). Weekend-scope prototype.

## Why this project

I want a prototype that:

- (a) solves a real customer pain — carrying forward "what I liked"
      across generations is genuinely hard
- (b) is satisfying for a real user (designer / mood-board creator)
      to use *to convergence* — not just for a 30-second demo. Sessions
      run 8-15 rounds; the loop has to stay coherent, not drift.

Audience: designers and mood-board creators iterating on a single
image. Not a viral toy, not a generic AI-image novelty — a refinement
tool where the deliverable is the final image they couldn't have
gotten with one prompt.

## The core hypothesis

Luma's agents API exposes a single image-conditioning primitive
(`image_ref`); UNI-1 interprets the user's intent from natural-language
prompts. When a user prefers image B over image A, the *interesting*
product problem is: **what shape of prompt encodes the kind of
preference signal the user gave?**

- "I like B's mood but A's subject" → a *preserve-look* prompt
  (e.g. "similar mood and lighting, different subject")
- "I like B's whole subject" → a *preserve-subject* prompt
  (e.g. "the same character/object, different scene")
- "I like B but want it bolder" → a *tweak* prompt (e.g. "the same
  image but moodier")

An LLM proposes the strategy and writes the resulting prompt. The
user can override the strategy. The build will surface findings about
when this language-only routing is right and when it isn't.

This is a deliberate pivot from an earlier draft that assumed three
distinct API channels (`style_ref` / `character_ref` /
`modify_image_ref`). Luma migrated to a single `image_ref` primitive
in their April 2026 agents API; the spike (Unit 1) surfaced this on
day 0 — exactly what the spike is for. Routing now happens entirely
in language, which makes the hypothesis *harder* and arguably more
interesting: the LLM has to encode strategy choice into prose UNI-1
will honor, not into a structured field.

## MVP scope (what ships)

The single bet: **anchored A/B refinement loop on a single image.**

### In scope
- Text prompt → two parallel UNI-1 generations (round 0, no anchor)
- Click-to-pick A/B UI
- Anchored loop: winner persists as A, one new candidate generated as
  B each subsequent round (round-N calls UNI-1 with `image_ref` set
  to the winner URL).
- LLM reasoning step per round: given (prompt, current winner, last
  runner-up), output JSON `{rationale, strategy, instruction}` where
  `strategy ∈ {preserve_look, preserve_subject, tweak}`. The
  strategy is metadata for UI/logging/override; the `instruction`
  is the actual next-round prompt the LLM writes in that strategy's
  shape.
- Chosen strategy and rationale revealed *after* B generates (subtitle
  on B, e.g. *"Kept the look because: …"*). Override dropdown applies
  to the *next* round, not the current one — the user's escape hatch
  when Claude misroutes.
- "Done" button → PNG download.
- README with `uv run` (backend) + `npm run dev` (frontend) setup.
- `NOTES.md` capturing weird findings as I build.

### Explicitly NOT in MVP (v2 ideas, mention in README)
- Ray 2 video output ("finalize" → image-to-video)
- User-uploaded starting images (requires CDN hosting)
- PDF export
- Branching from arbitrary points in history
- Auth, accounts, server-side persistence
- Twitter / social share intent — wrong audience for this build
- Speculative pre-generation of round N+1 to mask latency
  (interesting if 8-15 round sessions feel slow; YAGNI for MVP)
- **Preference chip** (`mood` / `subject` / `composition` / `bolder`)
  feeding the strategy prompt — was insurance against an unproven
  risk; add only if Unit 6 shows the LLM-alone path is wobbly.
- **"Both bad" re-roll button** — escape hatch; substitute is "pick
  the less-bad one and override the strategy for next round".
- **History rail** with thumbnails + strategy badges — visual progress
  indicator; the active pair is the only thing that affects outcomes.

### Fast-follow (v2 candidates after the prototype ships)
- **Demo GIF in the README.** Record a 10-pick session and embed at
  the top of `README.md` as the project teaser.

## Why anchored A/B (not pure A/B)

Both options were on the table. Anchored wins because:
1. It mirrors how creative refinement actually feels — "this, but
   more X" — not blanking the canvas every round.
2. It makes "I'm done" a natural state. If B keeps losing,
   convergence is signaled by the user not picking it.
3. The optometrist analogy is actually anchored — they flip back to
   the previous lens to confirm.

## Stack

- React frontend (Vite, no SSR), TypeScript
- Python backend (FastAPI), Luma agents Python SDK (`luma-agents`)
- Anthropic Python SDK (`anthropic`) for the strategy-selection
  reasoning step, vision-capable model so it can see both images
- No hosted infra — anyone can clone and run with their own keys
- Personal GitHub repo

## Build plan 

### Pre-work: spike script

Single Python file, no UI, no FastAPI. Validates the loop works
end-to-end before committing to UI. See `spike/spike.py`:

1. Hardcode a prompt
2. Call UNI-1 twice in parallel, get two image URLs
3. Call Claude with both URLs + the prompt, get back the
   strategy + instruction JSON
4. Use the JSON to construct the next UNI-1 call with `image_ref`
   pointing at the winner
5. Print everything to console
6. On 5 hand-picked obvious A/B pairs, eyeball whether Claude's
   strategy pick agrees ≥3 times.

Go/no-go gate: ≥3/5 strategy agreement. If the LLM is shakier than
that, sharpen the prompt, pivot the README narrative ("why this is
harder than it looks"), or demote the LLM step to a simpler A/B
refiner — better to learn this on Day 0 than Sunday of Weekend 2.

Loop convergence is judged by *using* the prototype during Weekend
1/2, not by experiments here.

### 1 — the loop

- Day 1: FastAPI skeleton, Luma SDK wired (async client), basic
  `POST /generate` endpoint that does two parallel calls via
  `asyncio.gather`. React skeleton with prompt input and A/B
  display. Click-to-pick. End of day: round 0 works manually.
- Day 2: LLM reasoning step. Strategy selection + instruction
  authoring. Round N logic. End of weekend: full loop works
  end-to-end, ugly but functional.

### 2 — polish + ship

- Day 1: Strategy override UI, "Done" → PNG export, README.
- Day 2: NOTES.md cleanup, edge cases (API failures, slow
  generations), deploy-free path (`uv run` for backend +
  `npm run dev` for frontend), ship.

## Open technical questions to resolve early

Validate in the spike, not assume:

1. **Round-0 variance.** Does calling UNI-1 twice with identical input
   return two different images? If not, append distinct semantic
   seeds (`"warm lighting"` for A, `"cool lighting"` for B) — neutral
   nonces may collapse to the same latent.

2. **Does `image_ref` accept a `weight` field on the new agents API?**
   The current docs page lists `url` / `data` / `media_type` only; the
   old API had a `weight` knob. Probe empirically; if accepted,
   calibrate. If not, treat conditioning strength as a prompt-only
   knob (e.g. "loosely inspired by …" vs "matching exactly the
   composition of …").

(URL TTL is documented as 1 hour on the new API — already answered.)

Loop convergence and latency-feel are answered while *using* the
prototype — log surprises in `NOTES.md` as they happen.

## LLM reasoning step — design notes

The brain of the system is one LLM call per round. Tight contract:

**Inputs**: original text prompt, winner image URL, runner-up image
URL (both from previous round)

**System prompt** (sketch — refine during spike):

> You're helping refine an image generation. The user picked image B
> over image A, both generated from this prompt: "...". Reason about
> what's better in B compared to A. Then choose ONE strategy for the
> next round and write a self-contained image-generation prompt that
> embodies that strategy.
>
> Strategies:
> - `preserve_look`: keep B's visual style/mood/lighting, allow
>   subject variation. The prompt should describe the new subject
>   and inherit B's stylistic adjectives.
> - `preserve_subject`: keep B's subject identity, allow scene
>   variation. The prompt should name B's subject and describe a new
>   context.
> - `tweak`: surgical edit on B. The prompt should be a near-copy of
>   the original with a focused change ("the same image but moodier").
>
> Output JSON only:
> {
>   "rationale": "<1-2 sentences on why B won>",
>   "strategy": "preserve_look" | "preserve_subject" | "tweak",
>   "instruction": "<self-contained image-generation prompt for next round>"
> }

The backend uses `instruction` as the literal `prompt` argument to
the next UNI-1 call, with `image_ref=[{"url": <winner_url>}]`. The
`strategy` field is metadata — it drives the UI subtitle, the
override dropdown, and the gate-test ("did Claude pick the strategy I
would have?"). It does *not* dispatch to different API calls; the
new API has only one image-conditioning primitive.

## Reference: Luma API capabilities used

From https://docs.agents.lumalabs.ai/guides/image-generation/:

- `POST agents.lumalabs.ai/v1/generations` — text-to-image
- Model: `uni-1` (UNI-1)
- `type: "image"`, `output_format: "png"` (or others)
- `image_ref` — array of up to 9 reference entries; each entry has
  `{url}` *or* `{data, media_type}` (base64 inline). The only
  image-conditioning primitive on this API; UNI-1 interprets the
  reference's role from the prompt itself
- Image URLs in responses are presigned and expire after ~1 hour
- Polling: `GET agents.lumalabs.ai/v1/generations/{id}` until
  `state == "completed"`; the result URL is at `output[0].url`
- Auth: `Authorization: Bearer <LUMAAI_API_KEY>` header

## Success criteria

- The loop works end-to-end with no manual intervention.
- A designer can run **10+ rounds in a single session** without the
  loop drifting away from what they liked. Per-round latency feels
  like part of the craft, not a wait.
- README makes the project clone-and-run on any machine with
  Python 3.11+, Node, a Luma API key, and an Anthropic API key.
- `NOTES.md` has at least 5 substantive findings about UNI-1 / Luma
  agents API behaviour, with the strongest finding leading.

## Tone & style for the codebase

- Functional, not over-engineered. This is a prototype.
- TypeScript on the frontend, strict mode. No fancy state management
  — `useState` and prop drilling are fine for this scope.
- Python 3.11+ on the backend with type hints. Pydantic models for
  the LLM JSON response and request/response payloads.
- One file per major concern; don't preemptively split into
  packages.
- Comments explain *why*, not *what*.
- README should read like a blog post, not a reference manual.
