# image-morpher — Project Brief

## What this is

image-morpher is an A/B image refinement loop built on Luma's API.

You describe an image in words. You get two versions. You pick the one
you like more. That winner stays on screen as your anchor — the new "A" —
and a new candidate "B" is generated alongside it, refined in the
direction of what you liked. You keep picking until you're happy, then
export.

The interesting part is what happens between rounds: an LLM looks at both
images, reasons about why you picked the winner, and decides which of
Luma's reference channels to use for the next generation — style,
character, or surgical edit. You can override its choice. Each round the
search space narrows. You're doing gradient descent on an image, with
yourself as the loss function.

Built on the Dream Machine API (Photon image generation, with UNI-1
reference primitives). Weekend-scope prototype.

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

Luma's API exposes three different reference channels:
`style_ref`, `character_ref`, `modify_image_ref` (plus generic
`image_ref`). The docs don't tell you when to use which. When a user
prefers image B over image A, the *interesting* product problem is:
**which reference channel does the user's preference signal map to?**

- "I like B's mood but A's subject" → `style_ref` from B,
  `character_ref` from A
- "I like B but want it bolder" → `modify_image_ref` on B with a
  text diff
- "I like B's whole vibe" → `image_ref` from B with high weight

An LLM proposes the lever. The user can override. The build will
surface real findings about when this routing is right and when it
isn't.

## MVP scope (what ships)

The single bet: **anchored A/B refinement loop on a single image.**

### In scope
- Text prompt → two parallel Photon generations (round 0, no anchor)
- Click-to-pick A/B UI
- Anchored loop: winner persists as A, one new candidate generated as
  B each subsequent round
- LLM reasoning step per round: given (prompt, current winner, last
  loser), output JSON `{rationale, lever, instruction}` where
  lever ∈ {style_ref, character_ref, modify_image_ref}. Per-lever
  weight defaults live in backend config, calibrated empirically
  (logged in NOTES.md), *not* asked of the LLM — it has never seen
  what 0.3 vs 0.7 looks like on Luma.
- LLM lever and rationale revealed *after* B generates (subtitle on B,
  e.g. *"Went with `style_ref` because: …"*). Override dropdown applies
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
  feeding the lever prompt — was insurance against an unproven risk;
  add only if Unit 6 shows the LLM-alone path is wobbly.
- **"Both bad" re-roll button** — escape hatch; substitute is "pick
  the less-bad one and override the lever for next round".
- **History rail** with thumbnails + lever badges — visual progress
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
- Python backend (FastAPI), Luma Python SDK (`lumaai>=1.21`)
- Anthropic Python SDK (`anthropic`) for the lever-selection reasoning
  step, vision-capable model so it can see both images
- No hosted infra — anyone can clone and run with their own keys
- Personal GitHub repo

## Build plan 

### Pre-work: spike script

Single Python file, no UI, no FastAPI. Validates the loop works
end-to-end before committing to UI. See `spike/spike.py`:

1. Hardcode a prompt
2. Call Photon twice in parallel, get two image URLs
3. Call Claude with both URLs + the prompt, get back the lever JSON
4. Use the JSON to construct the next Photon call (round 1)
5. Print everything to console
6. On 5 hand-picked obvious A/B pairs, eyeball whether Claude's lever
   pick agrees ≥3 times.

Go/no-go gate: ≥3/5 lever agreement. If the LLM is shakier than that,
sharpen the prompt, pivot the README narrative ("why this is harder
than it looks"), or demote the LLM step to a simpler A/B refiner —
better to learn this on Day 0 than Sunday of Weekend 2.

Loop convergence is judged by *using* the prototype during Weekend
1/2, not by experiments here.

### 1 — the loop

- Day 1: FastAPI skeleton, Luma SDK wired (async client), basic
  `POST /generate` endpoint that does two parallel calls via
  `asyncio.gather`. React skeleton with prompt input and A/B
  display. Click-to-pick. End of day: round 0 works manually.
- Day 2: LLM reasoning step. Lever selection. Round N logic. End of
  weekend: full loop works end-to-end, ugly but functional.

### 2 — polish + ship

- Day 1: Lever override UI, "Done" → PNG export, README.
- Day 2: NOTES.md cleanup, edge cases (API failures, slow
  generations), deploy-free path (`uv run` for backend +
  `npm run dev` for frontend), ship.

## Open technical questions to resolve early

Validate in the spike, not assume:

1. **Round 0 variance.** Does calling Photon twice with identical
   input return two different images? If not, append distinct
   semantic seeds (`"warm lighting"` for A, `"cool lighting"` for B)
   — neutral nonces may collapse to the same latent.

2. **`style_ref` weight calibration.** What value feels like "carry
   the vibe" vs "near-duplicate"? Probe empirically; bake into
   `config.py`; log the trio in `NOTES.md`.

3. **Image URL TTL.** Do Luma URLs survive ~30 min from generation?
   If shorter, document it in the README. Don't build a proxy.

Loop convergence and latency-feel are answered while *using* the
prototype — log surprises in `NOTES.md` as they happen.

## LLM reasoning step — design notes

The brain of the system is one LLM call per round. Tight contract:

**Inputs**: original text prompt, winner image URL, loser image URL
(both from previous round)

**System prompt** (sketch — refine during spike):

> You're helping refine an image generation. The user picked image B
> over image A, both generated from this prompt: "...". Reason about
> what's better in B compared to A. Then propose ONE refinement for
> the next round.
>
> Choose exactly one of these reference channels:
> - `style_ref`: preserve B's visual style, allow subject variation
> - `character_ref`: preserve B's subject identity, allow scene
>   variation
> - `modify_image_ref`: surgical edit on B following a text
>   instruction
>
> Output JSON only:
> {
>   "rationale": "<1-2 sentences on why B won>",
>   "lever": "style_ref" | "character_ref" | "modify_image_ref",
>   "instruction": "<text instruction for the next generation>"
> }

The JSON output deterministically routes to the correct Luma API
call construction in the backend. `weight` is *not* asked of the LLM
— per-lever defaults live in backend config (calibrated empirically;
see open question #2).

## Reference: Luma API capabilities used

From https://docs.lumalabs.ai/docs/image-generation:

- `POST /dream-machine/v1/generations/image` — text-to-image
  (Photon)
- `image_ref`: up to 4 image URLs, each with `weight` (general
  vibe carry-forward)
- `style_ref`: image URL + weight (visual style only)
- `character_ref`: identity-keyed dict, up to 4 images per
  identity (subject identity)
- `modify_image_ref`: single image URL + text prompt + weight
  (surgical edit)
- All ref images must be public CDN URLs — Luma does not accept
  uploads
- Responses are async; poll generation by ID or use `callback_url`

## Success criteria

- The loop works end-to-end with no manual intervention.
- A designer can run **10+ rounds in a single session** without the
  loop drifting away from what they liked. Per-round latency feels
  like part of the craft, not a wait.
- README makes the project clone-and-run on any machine with
  Python 3.11+, Node, a Luma API key, and an Anthropic API key.
- `NOTES.md` has at least 5 substantive findings about UNI-1 / Photon
  behaviour, with the strongest finding leading.

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
