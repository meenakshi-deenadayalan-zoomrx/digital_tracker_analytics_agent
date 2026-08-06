# DTAA Chat Extractor — How to Use

Extracts HCP questions and AI responses from MedAI platforms (currently OpenEvidence) captured by the Digital Tracker. Each question–answer pair becomes one row in the output.

---

## Setup

1. Copy the skill to your Claude skills directory:
   ```bash
   cp -r skills/dtaa-chat-extractor ~/.claude/skills/
   ```
2. Restart Claude Code (or reload skills).

---

## How to Activate

Type a message like one of these in Claude:

> "Extract MedAI conversations from OpenEvidence for Q1 2025"
> "Pull HCP questions and AI responses from OpenEvidence for project 42"
> "Export chat data from OpenEvidence between Jan and March 2025"

Claude will activate the Chat Extractor skill automatically.

---

## What Claude Will Ask You

Before running, Claude confirms the parameters:

| Parameter | Required? | Default |
|---|---|---|
| Platform(s) | No | OpenEvidence |
| Date range | **Yes** | — |
| Project ID | Recommended | All users |
| User ID | No | All users |
| Session | No | All sessions |

**Always provide a project ID** when extracting data for a specific client — without it, the query returns data for all users in the system.

---

## What You Get Back

A markdown table with one row per Q&A pair:

| Column | What it is |
|---|---|
| `web_content_id` | ID of the tracked webpage |
| `user_id` | HCP who visited the page |
| `session` | Tracker session number |
| `visited_timestamp` | When the page was visited |
| `absolute_url` | Full URL of the conversation page |
| `duration` | Time spent on the page |
| `search_query_id` | Unique ID for this question (`{web_content_id}_{n}`) |
| `search_query` | The HCP's exact question |
| `ai_response_id` | Unique ID for this answer (`{web_content_id}_{n}`) |
| `ai_response` | The platform's exact AI response |

Pages with multiple Q&A rounds produce multiple rows (one per round), all sharing the same `web_content_id`.

---

## Example Request

```
Extract OpenEvidence conversations for project 99, January 2025 to March 2025.
```

Claude will confirm parameters, run the query in batches of 10, and return a table like:

| web_content_id | user_id | search_query | ai_response |
|---|---|---|---|
| 12345 | 42 | What are first-line treatments for psoriasis? | First-line treatments include topical corticosteroids... |
| 12345 | 42 | Are biologics preferred over topicals? | Biologics are preferred when moderate-to-severe... |
| 12346 | 87 | Causes of belching | Belching is a common symptom with multiple causes... |

---

## Edge Cases Claude Handles Automatically

| Situation | What happens |
|---|---|
| Page captured mid-load (response not rendered yet) | `ai_response = NULL`; logged as skipped |
| Dashboard or nav page (no conversation) | `search_query = NULL`; logged as skipped |
| Multi-turn conversation (multiple Q&A rounds) | One row per round, numbered `_1`, `_2`, etc. |
| Very long AI response | Captured in full — not truncated |
| Empty or missing extracted text | Null row returned; logged as skipped |

A **batch summary** is printed at the end of each query run:
```
Batch summary: 10 processed, 14 pairs extracted, 2 skipped, 0 warnings
```

---

## Adding a New Platform

1. Open `references/medai_platforms.md`
2. Copy the OpenEvidence block and fill in the fields for the new platform
3. Add the platform's URL regexp to the **Combined URL REGEXP** section at the bottom of that file
4. Reinstall the skill: `cp -r skills/dtaa-chat-extractor ~/.claude/skills/`

No changes to `SKILL.md` are needed — the skill reads platform config from `medai_platforms.md` at runtime.

---

## What This Skill Does NOT Do

- It does **not** compute SOV, Reach, or Frequency — use the `dtaa-<channel>-metrics` skills for that.
- It does **not** summarize or paraphrase responses — all text is extracted verbatim.
- It does **not** filter by HCP specialty beyond excluding internal/test users (specialty IDs 28, 30).
