# online — single multitask 260M (Bangla+English+Code+Creative 50/50) + gated NSFW LoRA-B

Folders created. Raw zips untouched in root. Heavy work runs on Kaggle (see `data/work/RUNBOOK.md`).

- `data/work/skill_map.json` — which zip trains which skill; `(29)` quarantined, `(30)` excluded from LLM.
- `data/work/staged_manifest.json` — caps/sampling/dedup/mix.
- `data/work/clean_filter.py` — SFW + NSFW-quarantine filter.
- `data/work/nsfw_manifest.json` + `nsfw_policy.md` + `download_nsfw_kaggle.sh` — NSFW text track (Kaggle-only).
- `db/schema.sql`, `gateway/router.py` — Neon state + prompt router stubs.
- `models/` — reserved for base-260M/gguf/adapters (final GGUF only, ~250MB).
