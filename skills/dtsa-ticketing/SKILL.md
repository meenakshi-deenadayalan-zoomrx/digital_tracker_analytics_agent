---
name: "DTSA Ticket Creation"
description: "Create Phabricator Maniphest tickets with DTSA diagnostic findings. Activate after completing an investigation to produce a structured ticket with evidence matrix, root cause analysis, and recommended actions."
---

# Ticket Creation

Use `dtsa_phabricator_create_task` after all investigation steps are complete.

## Tool Parameters

- `title`: `[DTSA] P{N} | {channel} | {platform} | {symptom}`
- `description`: full Remarkup-formatted body (see template in `references/remarkup_template.md`)
- `priority`: `unbreak_now` | `high` | `normal` | `low`
- `tags`: optional array of Phabricator project PHIDs

## Priority Mapping

| Score | Priority | API Value |
|---|---|---|
| P1 (0.8–1.0) | Unbreak Now | `unbreak_now` |
| P2 (0.6–0.79) | High | `high` |
| P3 (0.3–0.59) | Normal | `normal` |
| P4 (0.0–0.29) | Low | `low` |

## Rules

1. **Always include the evidence matrix** — every finding needs sources + confidence label
2. **Use Remarkup** (Phabricator's format — `**bold**`, `//italic//`, `| table |`)
3. **Include raw volume data** as a comparison table (current vs. baselines)
4. **List all commits reviewed** with relevance scores, even LOW ones that were ruled out
5. **Selector results** — include element counts and bot detection status
6. **End with numbered action items** — each independently actionable

See `references/remarkup_template.md` for the full template.
