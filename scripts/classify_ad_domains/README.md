# Ad Destination Domain Classifier

Finds non-healthcare domains in `ads.destination_url` so they can be added to the ad ignore list. Designed for 10k+ unique domains with resumable checkpointing.

## Pipeline

```
schema  →  extract  →  heuristic  →  (loop: next → Claude classifies → submit)  →  report
```

State is persisted to `./state/` after every batch — safe to stop and resume.

## Setup

Uses the project's `.env` (same DB creds as the MCP server). No extra deps.

## Usage

### 1. Discover schema (first run only)
```bash
python classify_ad_domains.py schema
```
Prints `ads` table columns and searches for `%ignore%` / `%blocklist%` tables. If the ignore-list table name is non-standard, edit `config.json` (auto-created) and set `ignore_list_table` + `ignore_list_domain_column`.

### 2. Extract unique domains from last 6 months
```bash
python classify_ad_domains.py extract --batch-size 5000
```
Keyset-paginated. Excludes rows where `status = 'NOT_REQUIRED'` and any domain already in the ignore-list table. Run in background for large datasets:
```bash
nohup python classify_ad_domains.py extract > extract.log 2>&1 &
```

### 3. Tier A heuristic pass (free, no network)
```bash
python classify_ad_domains.py heuristic
# optional: also flag ad-tech infra domains (doubleclick, adsrvr, etc.)
python classify_ad_domains.py heuristic --mark-adtech
```
Auto-classifies well-known non-healthcare brands (Amazon, Netflix, Chase, etc.) with `confidence=high`.

### 4. Classify remaining domains (Claude-driven)
```bash
python classify_ad_domains.py next --batch-size 25 > batch.json
```
Emits a JSON batch with domains sorted by ad-volume (highest-impact first). Claude then:
- `WebFetch https://<domain>/` asking whether it's healthcare/pharma/HCP content
- Optionally `WebSearch` for ambiguous brands
- Writes `results.json` = `[{domain, classification, confidence, evidence}, ...]`
  - `classification` ∈ `non_healthcare | healthcare | uncertain`
  - `confidence` ∈ `high | medium | low`
- `python classify_ad_domains.py submit results.json`

Repeat until `remaining: 0`. Each batch checkpoints, so interruptions are fine.

### 5. Final report
```bash
python classify_ad_domains.py report
```
Produces:
- `state/ignore_candidates.md` — full classification table (non-healthcare / healthcare / uncertain sections)
- `state/ignore_list_additions.txt` — newline-separated domains with `non_healthcare` + `confidence=high` (ready to append to the ignore list)

## Only `confidence=high + non_healthcare` makes it into the additions file

Everything else goes to either the healthcare section (keep processing ads for these) or the uncertain section (needs human review). This keeps false-positive risk at zero per your "100% confident" requirement.

## Re-runs

- `extract` is incremental — safe to re-run; only new rows scanned.
- `state/domains.json` is the single source of truth. Delete it to start fresh.
- `config.json` is re-read each run — tweak lookback months, table names, etc. without code edits.
