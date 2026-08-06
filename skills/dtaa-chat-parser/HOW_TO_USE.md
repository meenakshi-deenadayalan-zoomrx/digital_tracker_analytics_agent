# DTAA Chat Parser — How to Use

Parses HCP questions and AI responses from a file of captured MedAI page text (e.g. exported from the Digital Tracker database). Each question–answer pair becomes one row in the output.

Use this skill when you already have the raw page text in an Excel or CSV file. If you need to pull data directly from the database, use `/dtaa-chat-extractor` instead.

---

## Setup

1. Pull the latest repo:
   ```bash
   git pull
   ```
2. Copy the skill to your Claude skills directory:

   **macOS / Linux**
   ```bash
   cp -r /path/to/dtsa-mcp-server/skills/dtaa-chat-parser ~/.claude/skills/
   ```

   **Windows**
   ```
   xcopy /E /I C:\path\to\dtsa-mcp-server\skills\dtaa-chat-parser %USERPROFILE%\.claude\skills\dtaa-chat-parser
   ```

3. Restart Claude Code (or reload skills).

> If you followed the full SETUP.md, Step 5's `dtaa*` glob already installs this skill — just re-run that step after `git pull`.

---

## Input File Format

Your Excel (.xlsx) or CSV (.csv) file must have these columns:

| Column | Required | Description |
|---|---|---|
| `web_content_id` | Yes | Unique ID for each captured webpage |
| `absolute_url` | Yes | Full URL — used to select the correct parsing pattern |
| `extracted_text` (or `text`) | Yes | Raw text captured from the page |
| Any other columns | No | Passed through to output unchanged |

Any additional columns (e.g. `user_id`, `visited_timestamp`, `duration`) are carried through to the output as-is.

---

## How to Activate

Type a message like one of these in Claude Code:

> "Parse MedAI conversations from this file: C:\Reports\ojjaara_q2.xlsx"
> "Extract HCP questions from my Excel file of OpenEvidence pages"
> "I have a CSV with extracted_text, can you pull out the Q&A pairs?"

Claude will activate the Chat Parser skill automatically.

---

## What Claude Will Ask You

If you haven't provided a file path, Claude will ask:

> "Please share the file path — I need an Excel (.xlsx) or CSV (.csv) with columns: web_content_id, absolute_url, extracted_text."

Claude then confirms the column mapping before parsing:

```
File path:      C:\Reports\ojjaara_q2.xlsx
web_content_id: web_content_id
absolute_url:   absolute_url
extracted_text: extracted_text
Output:         table in chat

Confirm to proceed or provide changes.
```

---

## What You Get Back

A markdown table with one row per Q&A pair:

| Column | What it is |
|---|---|
| `web_content_id` | ID of the tracked webpage |
| `absolute_url` | Full URL of the conversation page |
| *(any extra input columns)* | Passed through unchanged |
| `search_query_id` | Unique ID for this question (`{web_content_id}_{n}`) |
| `search_query` | The HCP's exact question |
| `ai_response_id` | Unique ID for this answer (`{web_content_id}_{n}`) |
| `ai_response` | The platform's exact AI response |

> `extracted_text` is consumed during parsing and is not included in the output.

Pages with multiple Q&A rounds produce multiple rows (one per round), all sharing the same `web_content_id`.

---

## Requesting Excel Output

If you want the results written to a file rather than displayed in chat:

> "Parse my file and save the output as an Excel file"
> "Write the extracted pairs to ojjaara_q2_parsed.xlsx"

Claude will use the `anthropic-skills:xlsx` skill to write the output. Default output path: `{input_filename}_parsed.xlsx`.

---

## Example

**Request:**
```
Parse MedAI conversations from C:\Reports\ojjaara_q2.xlsx
```

**Output:**
```
Parsed 47 conversation pairs from 38 pages.
3 pages had no detectable conversation. 1 warning.

| web_content_id | absolute_url | search_query_id | search_query | ai_response_id | ai_response |
|---|---|---|---|---|---|
| 12345 | https://openevidence.com/ask/... | 12345_1 | What are first-line treatments for psoriasis? | 12345_1 | First-line treatments include topical corticosteroids... |
| 12345 | https://openevidence.com/ask/... | 12345_2 | Are biologics preferred over topicals? | 12345_2 | Biologics are preferred when moderate-to-severe... |
| 12346 | https://openevidence.com/ask/... | 12346_1 | Causes of belching | 12346_1 | Belching is a common symptom with multiple causes... |
```

---

## Edge Cases Claude Handles Automatically

| Situation | What happens |
|---|---|
| Page captured mid-load (response not rendered) | `ai_response = NULL`; logged as skipped |
| Dashboard or nav page (no conversation) | `search_query = NULL`; logged as skipped |
| Multi-turn conversation | One row per round, numbered `_1`, `_2`, etc. |
| Very long AI response | Captured in full — not truncated |
| Empty or missing `extracted_text` | Null row returned; logged as skipped |
| Unrecognized platform URL | Generic fallback parsing applied; logged as warning |

A summary is printed at the end:
```
Total: 38 processed, 47 pairs extracted, 3 skipped, 1 warning
```

---

## Adding a New Platform

1. Open `references/medai_platforms.md` inside the skill folder
2. Copy the OpenEvidence block and fill in the fields for the new platform
3. Add the platform's URL regexp to the **Combined URL REGEXP** section at the bottom
4. Reinstall the skill (re-run the copy command above)

No changes to `SKILL.md` are needed — the skill reads platform config from `medai_platforms.md` at runtime.

---

## What This Skill Does NOT Do

- It does **not** query the database — use `/dtaa-chat-extractor` for that.
- It does **not** compute SOV, Reach, or Frequency — use the `dtaa-<channel>-metrics` skills for that.
- It does **not** summarize or paraphrase responses — all text is extracted verbatim.
