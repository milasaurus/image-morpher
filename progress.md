# Progress

Last touched: 2026-05-15

## Unit status

| Unit | Status | Notes |
|------|--------|-------|
| 1 — Spike | ✅ Done | Two open spike questions remain (see below); not blockers for Unit 4 |
| 2 — API scaffold + Luma wrapper | ✅ Done | 18 tests passing |
| 3 — Models, strategy, /api/round | ✅ Done | 18 tests passing |
| 4–6 — Single-file web UI | 🟡 In progress — needs manual smoke test | `web/index.html` written; servers running |

## Before starting Unit 4

Three items were added to the plan on 2026-05-15 that haven't been
implemented yet. Knock these out first:

- [ ] Extract `_SYSTEM_PROMPT` from `api/app/strategy.py` into
      `api/app/system_prompt.py` as a module-level constant `SYSTEM_PROMPT`.
- [ ] Extract `_POLL_INTERVAL` / `_POLL_TIMEOUT` from `api/app/luma.py`
      into `api/app/constants.py` (`POLL_INTERVAL_S`, `POLL_TIMEOUT_S`).
- [ ] Add `NUM_OF_ROUNDS: int = 10` to `api/app/config.py`.
- [ ] Add `GET /api/config` → `{"num_of_rounds": settings.NUM_OF_ROUNDS}`
      to `api/app/main.py`. Update CORS middleware to allow `GET` in
      addition to `POST`.

## Unit 1 open questions (not blockers)

- [ ] **Round-0 variance.** Eyeball the URLs from the last spike run to
      confirm A and B differ visibly. If near-identical, add semantic jitter
      in `spike/spike.py` (see comment block there).
- [ ] **`image_ref` weight.** Set `IMAGE_REF_WEIGHT = 0.6` in `spike/.env`
      and run a round-N call. If it errors, log it in `NOTES.md` and leave
      `IMAGE_REF_WEIGHT = None` in `api/app/config.py`. If it works,
      calibrate and log.

## Next action

The UI is written. Start the two servers and open the app:

```bash
# Terminal 1 — backend (port 8001)
cd api
uv run uvicorn app.main:app --port 8001 --reload

# Terminal 2 — file server (port 8080)
cd web
python3 -m http.server 8080
```

Open http://localhost:8080 in the browser and run the manual smoke test:
prompt → 10 picks (mix all 3 strategies) → Done → image opens.

## Where things live

- `docs/project-brief.md` — vision and scope
- `docs/plan.md` — implementation plan (source of truth for each unit)
- `NOTES.md` — spike findings and open questions
- `spike/` — Unit 1 spike (reference for Luma SDK surface)
- `api/app/` — backend (FastAPI + Luma + Anthropic)
- `api/tests/` — 18 passing tests
- `web/` — frontend (not yet created)
