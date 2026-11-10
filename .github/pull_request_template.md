## Variant

- Folder: `variants/...`
- Owner:
- Reviewer (rotation):

## Checklist (CLAUDE.md rule 6)

- [ ] One change relative to `baseline/` (or this is `combined/`)
- [ ] No edits to `baseline/` or another member's folder
- [ ] Nothing trained or tuned on `dev.txt`
- [ ] No repo-specific logic (FastAPI, Rich, Requests, HTTPX)
- [ ] Smoke set runs with no crashes; average time per task: ___ min (< ~6)
- [ ] Dev score: ___ (baseline: ___), logged in the team experiment log
- [ ] `agent.yaml` validates; zip has `agent.yaml` at the root
- [ ] Only allowed tools used
