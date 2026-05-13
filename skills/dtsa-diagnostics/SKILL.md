---
name: "DTSA Diagnostic Methodology"
description: "Structured investigation playbook for Digital Tracker tracking issues. Activate for any systematic diagnosis: volume drop, zero volume, selector break, data quality issue, or latency problem. Covers intake through ticket creation."
---

# DTSA Investigation Playbook

**Critical rule: verify the problem exists in data before touching code.**

```
Step 1: Intake
Step 2: DB Volume Check      ← ALWAYS first. No code until this confirms a real drop.
Step 3: Selector Validation  ← email / search_results / ads channels only
Step 4: Commit Analysis      ← Only if Steps 2–3 don't fully explain the cause
Step 5: Code Reading         ← Only for commits flagged HIGH/MEDIUM relevance
Step 6: Impact Scoring
Step 7: Synthesis
Step 8: Ticket Creation
```

---

## Step 1: Intake

Extract from the PO's message:
- **Channel**: `web_contents` | `ads` | `email` | `search_results` | `social_posts`
- **Platform**: `chrome` | `ios` | `macos` | `all`
- **Timeframe**: when did the issue start?
- **Symptom**: `volume_drop` | `zero_volume` | `partial_degradation` | `data_quality` | `latency`

If channel and platform are clear from context, do not ask again.

---

## Step 2: DB Volume Check — ALWAYS FIRST

Load `/dtsa-database` for query patterns and schema.

Query 3 windows: current period, 1 week prior, 4 weeks prior.

| Pattern | Classification | Next step |
|---|---|---|
| Current = 0, baseline > 0 | `HARD_STOP` | Proceed to Step 3 |
| Current < 50% of baseline | `SEVERE_DEGRADATION` | Proceed to Step 3 |
| Current 50–80% of baseline | `PARTIAL_DEGRADATION` | Proceed to Step 3 |
| Current ≈ baseline (±20%) | `NORMAL` | **Stop** — return data to PO |
| Drop only on specific days | `DOW_EFFECT` | Likely not a bug — confirm with PO |

Tell the PO the classification before proceeding.

---

## Step 3: Selector Validation

Load `/dtsa-selectors` for the inventory.

Run only for DOM-dependent channels: **email**, **search_results**, **ads**.
Skip for `web_contents` and `social_posts` unless specifically suspected.

- `element_count = 0` → selector broken → strong evidence of DOM change
- Bot detection triggered → record INCONCLUSIVE, do not retry

---

## Step 4: Commit Analysis

Only reach this step if:
- DB confirms a real drop (not NORMAL/DOW_EFFECT), AND
- Selector validation doesn't fully explain the cause

Use `dtsa_github_commits` with `since` = drop onset − 2 days, `until` = drop onset + 1 day.
Read `AGENT_CONTEXT.md` for the affected repo to identify HIGH/MEDIUM relevance files.

Relevance scoring:
- **HIGH**: commit touches the entry-point file for the affected channel + platform
- **MEDIUM**: commit touches a shared helper/utility used by the channel
- **LOW**: unrelated files — skip

For each HIGH/MEDIUM commit, use `dtsa_github_diff`.

---

## Step 5: Code Reading

After identifying a suspicious diff, use filesystem tools for full context.
Have a specific question before calling any tool.

- `dtsa_read_file("<repo>/AGENT_CONTEXT.md")` — start here for any repo
- `dtsa_read_file(path)` — read a specific file; use `start_line`/`end_line` for large files
- `dtsa_grep_repo(repo, pattern)` — find all call sites of a removed/changed function
- `dtsa_list_repo_files(repo, subpath)` — explore structure if path is uncertain

Deep-dive docs: each `AGENT_CONTEXT.md` links to `docs/*.md` — read those for flow context.

---

## Step 6: Impact Scoring


```
impact_score = (
    0.35 * volume_factor     +  # % drop from baseline, 0–1
    0.25 * duration_factor   +  # hours affected, 0–1 (cap at 72h)
    0.20 * user_factor       +  # % of user base affected, 0–1
    0.10 * channel_factor    +  # email=1.0, ads=0.8, search=0.8, web=0.6, social=0.5
    0.10 * quality_factor       # complete loss=1.0, degraded=0.5
)
```

| Score | Priority |
|---|---|
| 0.8–1.0 | P1 — Unbreak Now |
| 0.6–0.79 | P2 — High |
| 0.3–0.59 | P3 — Normal |
| 0.0–0.29 | P4 — Low |

---

## Step 7: Synthesis

Label each finding:
- **CONFIRMED**: direct evidence from ≥2 independent sources
- **LIKELY**: strong single-source with temporal/causal correlation
- **INCONCLUSIVE**: single weak signal, conflicting data, or validation blocked

Evidence matrix format:
| Finding | Evidence Sources | Confidence | Impact |
|---|---|---|---|
| Gmail selector `h2.hP` no longer matches | Playwright count=0 + HARD_STOP | CONFIRMED | P1 |

If material ambiguities remain: ask max 2 clarification rounds, batch all questions.

---

## Step 8: Ticket Creation

Load `/dtsa-ticketing` for the Remarkup template and priority mapping.
Use `dtsa_phabricator_create_task`.

See `references/service_map.json` for channel → implementation mapping.
See `references/channel_reference.md` for cross-repo flow links.
