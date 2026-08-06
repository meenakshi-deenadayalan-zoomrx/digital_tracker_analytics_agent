---
name: "DTAA Chat Parser"
description: "Parses structured HCP ↔ MedAI conversation pairs (search queries and AI responses) from an Excel or CSV file. Input must have columns: web_content_id, absolute_url, and extracted_text (raw page text). Returns one row per Q&A pair. Activate when a user provides a file of captured MedAI page text and wants the conversations extracted. Do NOT activate for database queries — use dtaa-chat-extractor for that. Do NOT activate for SOV/Reach/Frequency metrics."
---

# DTAA — Chat Parser (File Input)

You parse structured HCP ↔ MedAI conversation pairs from an Excel or CSV file.

Each row in the input file contains a `web_content_id`, `absolute_url`, and the raw `extracted_text` from a captured MedAI webpage (e.g. OpenEvidence). Your job is to detect conversation structure in that text and return one row per Q&A pair — no summarization, no rewording.

---

## Tools

| Tool | Use |
|---|---|
| `anthropic-skills:xlsx` | Read input Excel file; write output Excel file |
| `Read` | Read input if the file is CSV |

---

## Workflow Overview

| Phase | Action |
|---|---|
| 1. Confirm file | Identify file path and column mapping; confirm with user |
| 2. Read file | Load rows from Excel/CSV |
| 3. Parse conversations | Detect Q&A pairs from raw text using platform-aware patterns |
| 4. Format output | Return one row per pair; optionally write back to Excel |

---

## Phase 1 — Confirm File

Before reading any data, confirm:

```
I'll parse MedAI conversations from your file:

File path:         [absolute path to .xlsx or .csv]
web_content_id:    [column name — default: "web_content_id"]
absolute_url:      [column name — default: "absolute_url"]
extracted_text:    [column name — default: "extracted_text" or "text"]
Extra columns:     [any additional columns present — passed through to output unchanged]
Output:            [table in chat / new Excel file / add columns to input file]

Confirm to proceed or provide changes.
```

Skip confirmation only if the user provides all parameters explicitly and no ambiguity exists.

If the user has not provided a file path, ask:
> "Please share the file path — I need an Excel (.xlsx) or CSV (.csv) with columns: web_content_id, absolute_url, extracted_text."

---

## Phase 2 — Read File

### Excel (.xlsx)

Use the `anthropic-skills:xlsx` skill to read the file. Request all rows and note the column names.

### CSV (.csv)

Use the `Read` tool to read the file as plain text, then parse header + rows from comma-separated values.

### Required columns

| Column | Required | Notes |
|---|---|---|
| `web_content_id` | Yes | Unique ID for each captured page |
| `absolute_url` | Yes | Used to identify the platform and select the correct parsing pattern |
| `extracted_text` (or `text`) | Yes | Raw captured page text to parse |
| Any other columns | No | Passed through unchanged to output |

If any required column is missing, stop and ask the user to confirm the correct column names before proceeding.

### Batch size

Process all rows. If the file has more than 50 rows, process in batches of 20 rows and report progress after each batch.

---

## Phase 3 — Parse Conversations

For each row, parse `extracted_text` to identify HCP ↔ AI conversation pairs.

### Step 3a — Load Platform Config

Read `references/medai_platforms.md` and match each row's `absolute_url` against the platform entries:
- If a match is found → use that platform's anchors and noise patterns
- If no match → apply generic fallback patterns below

> If `absolute_url` is empty or NULL, apply generic fallback patterns.

### Step 3b — Strip Noise

Before parsing, strip:
- Platform noise sections (nav chrome, sidebar lists, copyright, announcements)
- UI chrome lines: ≤ 3 words AND not part of a sentence (e.g., "Home", "Sign in", "Back")
- Timestamps and pagination markers

### Step 3c — Detect Conversation Turns

Apply patterns in priority order (stop at first successful match):

**Priority 1 — OpenEvidence structural pattern** (confirmed from live data)

OpenEvidence does NOT use explicit `You:` / `AI:` labels. The structure is:

```
[Nav chrome] [Sidebar conversation list] [User email]
"New Conversation" OR "Share New Conversation"
[optional digit 1–10]   ← ad indicator, NOT part of the question — strip it
[QUESTION TEXT]
"Finished thinking" OR "Analyzing query" OR "Answered on [date]"
"Searching published medical literature, guidelines, FDA, CDC, and more"
"Synthesizing relevant information"
"Done"
[AI RESPONSE TEXT]
"References" OR "Follow-Up Questions" OR "Would you like me" OR "Inbox"
```

**Question extraction rule**: Text between the ad-indicator / "New Conversation" anchor and the next occurrence of `Finished thinking`, `Analyzing query`, or `Answered on`.

**Nav-bleed fix**: Some pages start with `New Conversation` as the very first word of the nav bar (e.g., `New Conversation Visits New Visit Calculators Collections CME 50.0 Dotflows...`). If the nav noise anchor fails to match exactly (the nav text varies between app versions), the parser will find `New Conversation` at position 0 and the entire sidebar — conversation history titles, user email, the next `Share New Conversation` anchor, and the real question — all become the "question candidate". Detect this by checking whether the extracted question candidate itself contains `"Share New Conversation"` or `"New Conversation"`. If it does, strip to the **last** such occurrence within the candidate, then apply the ad-indicator strip again. That remaining text is the real question.

**Answer extraction rule**: Text immediately after `Done` up to the first occurrence of `References`, `Follow-Up Questions`, `Would you like me`, or `Inbox`.

**Multi-turn pages**: The full pattern repeats for each exchange. Each `[question] → [thinking] → Done → [response]` cycle is one pair. Number them sequentially.

**Pages captured mid-load**: If `Finished thinking` / `Analyzing query` appears but `Done` does not → `ai_response = NULL`.

**Priority 2 — Generic labeled markers** (fallback for non-OpenEvidence platforms)

Scan for explicit role labels:
```
User: / You: / HCP: / Doctor: / Question: / Search: / Q:
AI: / Assistant: / Response: / Answer: / A:
```

**Priority 3 — Structural block inference** (last resort, low confidence)

- First block ending with `?` or ≤ 200 chars → query
- Next substantial block (>50 chars) → response
- Log as `[WARN] confidence=inferred`

### Step 3d — Extract and Pair Turns

1. Group turns into (user_turn, ai_turn) pairs in order of appearance
2. Each consecutive (user → ai) = one conversation pair
3. User turn with no following AI turn → `ai_response = NULL`
4. AI turn with no preceding user turn → skip (orphaned); log as skipped
5. Preserve original wording exactly — no paraphrasing, no grammar cleanup

### Step 3e — Handle Empty Results

If no pairs detected:
- Return one row with `search_query = NULL`, `ai_response = NULL`
- Log: `[SKIP] web_content_id={id} reason=no_conversation_detected`

---

## Phase 4 — Format Output

### ID Generation

| Field | Format | Example |
|---|---|---|
| `search_query_id` | `{web_content_id}_{n}` | `12345_1`, `12345_2` |
| `ai_response_id` | `{web_content_id}_{n}` | `12345_1`, `12345_2` |

`n` must match between `search_query_id` and `ai_response_id` for the same pair.

### Output Columns

All input columns except `extracted_text` are passed through. Extracted columns are appended:

| Column | Source | Notes |
|---|---|---|
| `web_content_id` | Input file | Same for all pairs from the same page |
| `absolute_url` | Input file | Same for all pairs from the same page |
| *(any extra input columns)* | Input file | Passed through unchanged |
| `search_query_id` | Generated | `{web_content_id}_{n}` |
| `search_query` | Extracted | Exact original wording |
| `ai_response_id` | Generated | `{web_content_id}_{n}` |
| `ai_response` | Extracted | Exact original wording |

> `extracted_text` is consumed during parsing and dropped from the output.

### Output — Markdown table (default)

```
Parsed {total_pairs} conversation pairs from {total_pages} pages.
{n_skipped} pages had no detectable conversation. {n_warnings} warnings.

| web_content_id | absolute_url | search_query_id | search_query | ai_response_id | ai_response |
|---|---|---|---|---|---|
| 12345 | https://openevidence.com/ask/... | 12345_1 | What are the first-line treatments for psoriasis? | 12345_1 | First-line treatments for psoriasis include... |
```

### Output — Excel file (when user requests it)

Use `anthropic-skills:xlsx` to write parsed pairs to a new file or sheet:
- Default output path: `{input_filename}_parsed.xlsx`
- Default sheet name: `Parsed Pairs`

Ask the user for a preferred output path if not specified.

---

## Edge Cases

| Situation | Behavior |
|---|---|
| `extracted_text` is NULL or empty | Return one null row; log `[SKIP] reason=empty_extracted_text` |
| No conversation on page (login page, error page, dashboard) | Return one null row; log as skipped |
| Query only, no AI response (mid-load) | Capture query; `ai_response = NULL`, `ai_response_id = NULL` |
| Very long AI response (>2000 chars) | Capture full text; do not truncate |
| Imperfect OCR / garbled characters | Extract as-is; do not correct |
| Same `web_content_id` appears multiple times | Treat each row independently |
| `absolute_url` missing or unrecognized platform | Apply generic fallback; log `[WARN] unknown_platform` |
| Multi-turn page — more than one Q&A pair per row | Expand to multiple output rows, one per pair |

---

## Logging

```
[SKIP]  web_content_id=12345  reason=no_conversation_detected
[SKIP]  web_content_id=12346  reason=empty_extracted_text
[SKIP]  web_content_id=12347  reason=orphaned_ai_turn_only
[WARN]  web_content_id=12348  reason=inferred_structure_no_labels  confidence=low
[WARN]  web_content_id=12349  reason=unknown_platform  url=https://...
[ERROR] web_content_id=12350  reason=parse_exception  detail=malformed_unicode
```

Summary line at end:
```
Total: {n_processed} processed, {n_pairs} pairs extracted, {n_skipped} skipped, {n_warnings} warnings
```

---

## Validation Cases

### Case 1 — Single Q&A pair (standard)

**Input `extracted_text`**:
```
New Conversation ... Share New Conversation
What are the first-line treatments for psoriasis?
Finished thinking Analyzing query Searching ... Synthesizing relevant information Done
First-line treatments for psoriasis include topical corticosteroids...
References
```

**Expected**: `search_query = "What are the first-line treatments for psoriasis?"` | `ai_response = "First-line treatments for psoriasis include topical corticosteroids..."` | IDs = `{id}_1`

---

### Case 2 — Ad indicator stripped

**Input**: `... Share New Conversation 10\ncauses of belching\nFinished thinking ... Done\nBelching is a common symptom...\nFollow-Up Questions`

**Expected**: `search_query = "causes of belching"` (digit 10 stripped) | `ai_response = "Belching is a common symptom..."` (Follow-Up Questions not included)

---

### Case 3 — Multi-turn page

**Input**: Two full `[question → thinking → Done → response]` cycles in one `extracted_text`.

**Expected**: Two output rows with IDs `{id}_1` and `{id}_2`.

---

### Case 4 — Mid-load (no response)

**Input**: `... New Conversation 10\nbelching from lung cancer\nAnalyzing query Analyzing query`

**Expected**: `search_query = "belching from lung cancer"` | `ai_response = NULL` | Log: `[SKIP] reason=page_captured_mid_load`

---

### Case 5 — Dashboard page

**Input**: Nav/sidebar chrome only, no Q&A structure.

**Expected**: `search_query = NULL` | `ai_response = NULL` | Log: `[SKIP] reason=no_conversation_detected`

---

## References

- Platform config: `references/medai_platforms.md` — read this before every parsing run
