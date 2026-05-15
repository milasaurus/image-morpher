# Progress

Last touched: 2026-05-15

## Unit status

| Unit | Status | Notes |
|------|--------|-------|
| 1 — Spike | ✅ Done | Findings in NOTES.md |
| 2 — API scaffold + Luma wrapper | ✅ Done | 18 tests passing |
| 3 — Models, strategy, /api/round | ✅ Done | 18 tests passing |
| 4–6 — Single-file web UI | ✅ Done | Merged to main (PR #3) |

## Shipped

PR #3 merged 2026-05-15. Run with `make dev`, open http://localhost:8080.

## Where things live

- `docs/project-brief.md` — vision and scope
- `docs/plan.md` — implementation plan
- `NOTES.md` — findings
- `spike/` — Unit 1 spike
- `api/app/` — backend (FastAPI + Luma + Anthropic)
- `api/tests/` — 18 passing tests
- `web/` — frontend (vanilla JS, single file)
