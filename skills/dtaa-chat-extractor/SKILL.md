---
name: "DTAA Chat Extractor"
description: "Extracts structured HCP ↔ MedAI conversation pairs (search queries and AI responses) from raw webpage text stored in the Digital Tracker database. Activate when a user asks to extract, analyze, or export HCP questions and AI responses from MedAI platforms such as OpenEvidence. Do NOT activate for SOV/Reach/Frequency metrics — use the appropriate channel-metrics skill for those."
---

# DTAA — Chat Extractor

You extract structured HCP ↔ MedAI conversation pairs from raw webpage text captured by the Digital Tracker.

Webpages are from platforms like OpenEvidence where HCPs ask medical questions and receive AI-generated responses. Your job is to query the database, detect conversation structure in the raw text, and return one row per Q&A pair with clean, accurate extraction — no summarization, no rewording.

---

## MCP Tool

| Tool | Use |
|---|---|
| `dtsa_mysql_read` | All database queries — fetch web_contents + extracted_texts |

---

## Workflow Overview

| Phase | Action |
|---|---|
| 1. Confirm parameters | Identify platform, date range, and optional filters; confirm with user |
| 2. Fetch records | Query DB for matching web_contents + extracted_texts rows |
| 3. Parse conversations | Detect Q&A pairs from raw text using platform-aware patterns |
| 4. Format output | Return one row per pair with full base columns and extracted fields |

---

## Phase 1 — Confirm Parameters

Before running any query, confirm:

```
I'll extract MedAI conversations with the following parameters:

Platform(s):       [from references/medai_platforms.md — list active domains]
Date range:        [e.g., 2025-01-01 to 2025-03-31]
Project/Target:    [project_id if provided, otherwise ALL users]
User ID filter:    [user_id if provided]
Session filter:    [session if provided]
Batch size:        [default: 50 records per run]

Confirm to proceed or provide changes.
```

Skip confirmation only if the user provides all parameters explicitly and no ambiguity exists.

---

## Phase 2 — Fetch Records

### Platform REGEXP

Read `references/medai_platforms.md` to build the URL REGEXP. Combine all platform `url_regexp` values with `|`:

```
-- Single platform (current default):
openevidence\.com

-- Multi-platform example (when more are added):
openevidence\.com|medscape\.com
```

### Base SQL Query

> **⚠️ Critical — `extracted_texts` join**: The table uses the entity pattern, NOT a `web_content_id` column. Always join as: `et.entity_id = wc.id AND et.entity_type = 'WEB_CONTENT'`

```sql
SELECT
    wc.id          AS web_content_id,
    wc.user_id,
    wc.session,
    wc.visited_timestamp,
    wc.absolute_url,
    wc.duration,
    SUBSTRING(et.text, 1, 5000) AS extracted_text
FROM web_contents wc
JOIN extracted_texts et ON et.entity_id = wc.id AND et.entity_type = 'WEB_CONTENT'
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
WHERE wc.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
  AND wc.absolute_url REGEXP '{platform_regexp}'
  AND wc.visited_timestamp BETWEEN '{start} 00:00:00' AND '{end} 23:59:59'
ORDER BY wc.visited_timestamp ASC
LIMIT {batch_size} OFFSET {offset};
```

> **⚠️ Note on SUBSTRING**: Use `SUBSTRING(et.text, 1, 5000)` to keep result size manageable. For multi-turn pages the full text may be much longer; if a response appears truncated mid-sentence, re-query that specific `web_content_id` with a higher limit: `SUBSTRING(et.text, 1, 20000)`.

### Optional Filter Additions

Append inside the WHERE clause only when the user provides the value:

```sql
-- Project target list filter (ALWAYS add when project_id is known):
JOIN users u ON wc.user_id = u.id
JOIN project_target_list ptl ON u.npi = ptl.npi AND ptl.project_id = {project_id}

-- User filter:
AND wc.user_id = {user_id}

-- Session filter:
AND wc.session = {session}
```

> **⚠️ Critical**: When `project_id` is provided, always add the `project_target_list` join — omitting it returns data for all users in the system, not the client's target panel.

### Batch Processing

Default batch: **10 records per query** (`LIMIT 10 OFFSET 0`). Extracted text is large — 50 records will exceed the context window.

If the user requests more records or a full date range:
1. Run a COUNT query first to report total matches
2. Run in batches of 10, incrementing OFFSET by 10 each time
3. Parse and accumulate results across batches before presenting the final output

Count query:
```sql
SELECT COUNT(DISTINCT wc.id) AS total_records
FROM web_contents wc
JOIN extracted_texts et ON et.entity_id = wc.id AND et.entity_type = 'WEB_CONTENT'
JOIN user_speciality_mappings usm ON wc.user_id = usm.user_id
WHERE wc.type IN ('WEB_PAGE', 'HTML_WEB_PAGE')
  AND wc.user_wave_id IS NULL
  AND usm.speciality_id NOT IN (28, 30)
  AND wc.absolute_url REGEXP '{platform_regexp}'
  AND wc.visited_timestamp BETWEEN '{start} 00:00:00' AND '{end} 23:59:59';
```

---

## Phase 3 — Parse Conversations

For each row returned by the DB query, parse `extracted_text` to identify HCP ↔ AI conversation pairs.

### Step 3a — Load Platform Config

For each row, match `absolute_url` against the platform entries in `references/medai_platforms.md`:
- If a match is found → use that platform's `user_markers`, `ai_markers`, and `noise_sections`
- If no match → apply the generic fallback patterns below

### Step 3b — Strip Noise

Before parsing, remove noise content identified by the platform's `noise_sections` list. Strip:
- The matched section heading and all text beneath it until the next conversation turn
- Common UI chrome: lines that are ≤ 3 words AND are not part of a sentence (e.g., "Home", "Sign in", "Back")
- Copyright lines, timestamps, and pagination markers

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

**Multi-turn pages**: The full pattern repeats for each exchange. Each repeat of `[question] → [thinking] → Done → [response]` is one pair. Number them sequentially.

**Pages captured mid-load**: If `Finished thinking` / `Analyzing query` appears but `Done` does not, the page was captured before the response rendered → `ai_response = NULL`.

**Priority 2 — Generic labeled markers** (fallback for non-OpenEvidence platforms)

If no structural anchors are found, scan for explicit role labels:
```
User: / You: / HCP: / Doctor: / Question: / Search: / Q:
AI: / Assistant: / Response: / Answer: / A:
```

**Priority 3 — Structural block inference** (last resort, low confidence)

If neither structural anchors nor role labels are found:
- Identify blocks separated by blank lines
- The first block is the query if it ends with `?` or is ≤ 200 chars
- The next substantial block (>50 chars) is the response
- Log these pairs as `[WARN] confidence=inferred`

### Step 3d — Extract and Pair Turns

After detecting all turns:
1. Group turns into (user_turn, ai_turn) pairs in order of appearance
2. Each consecutive (user → ai) = one conversation pair
3. If a user turn has no following AI turn (incomplete page): capture query with `ai_response = NULL`
4. If an AI turn has no preceding user turn: skip it (orphaned response — log as skipped)
5. Preserve original wording exactly — do not paraphrase, summarize, or clean up grammar

### Step 3e — Handle Empty Results

If no conversation pairs are detected:
- Return a single row for that `web_content_id` with `search_query = NULL`, `ai_response = NULL`
- Log: `[SKIP] web_content_id={id} reason=no_conversation_detected`

---

## Phase 4 — Format Output

### ID Generation Rules

For each `web_content_id`, pairs are numbered sequentially in conversation order (1-indexed):

| Field | Format | Example |
|---|---|---|
| `search_query_id` | `{web_content_id}_{n}` | `12345_1`, `12345_2` |
| `ai_response_id` | `{web_content_id}_{n}` | `12345_1`, `12345_2` |

The running number `n` must match between `search_query_id` and `ai_response_id` for the same pair:
- Pair 1: `search_query_id = 12345_1`, `ai_response_id = 12345_1`
- Pair 2: `search_query_id = 12345_2`, `ai_response_id = 12345_2`

### Output Columns

| Column | Source | Notes |
|---|---|---|
| `web_content_id` | `web_contents.id` | Same for all pairs from the same page |
| `user_id` | `web_contents.user_id` | Same for all pairs from the same page |
| `session` | `web_contents.session` | Same for all pairs from the same page |
| `visited_timestamp` | `web_contents.visited_timestamp` | Same for all pairs from the same page |
| `absolute_url` | `web_contents.absolute_url` | Same for all pairs from the same page |
| `duration` | `web_contents.duration` | Same for all pairs from the same page |
| `search_query_id` | Generated | `{web_content_id}_{n}` |
| `search_query` | Extracted from text | Exact original wording |
| `ai_response_id` | Generated | `{web_content_id}_{n}` |
| `ai_response` | Extracted from text | Exact original wording |

### Output Format — Markdown Table

Present results as a markdown table. For large outputs (>10 pairs), summarize first:

```
Extracted {total_pairs} conversation pairs from {total_pages} pages.

| web_content_id | user_id | session | visited_timestamp | absolute_url | duration | search_query_id | search_query | ai_response_id | ai_response |
|---|---|---|---|---|---|---|---|---|---|
| 12345 | 42 | 7 | 2025-01-15 09:22:01 | https://openevidence.com/... | 00:03:45 | 12345_1 | What are the first-line treatments for psoriasis? | 12345_1 | First-line treatments for psoriasis include... |
| 12345 | 42 | 7 | 2025-01-15 09:22:01 | https://openevidence.com/... | 00:03:45 | 12345_2 | Are biologics preferred over topicals? | 12345_2 | Biologics are preferred when... |
```

---

## Edge Cases

| Situation | Behavior |
|---|---|
| Page with no conversation (e.g., login page, error page) | Return one null row; log as skipped |
| Partial conversation (query only, no AI response) | Capture query; set `ai_response = NULL` and `ai_response_id = NULL` |
| Very long AI response (>2000 chars) | Capture full text; do not truncate |
| Imperfect OCR (garbled characters, mid-word breaks) | Extract as-is; do not attempt to correct |
| Same page visited multiple times (duplicate web_content_id) | Each visit is a separate row with a separate ID; treat independently |
| extracted_text is NULL or empty string | Return null row; log as `[SKIP] reason=empty_extracted_text` |
| Platform not in medai_platforms.md but URL matches | Should not occur — URL filter prevents this. Log as `[WARN] unexpected_platform url={url}` if it somehow reaches parsing |

---

## Logging

Emit structured log entries for every anomaly. Include in the final response summary under a collapsible section:

```
[SKIP]  web_content_id=12345  reason=no_conversation_detected
[SKIP]  web_content_id=12346  reason=empty_extracted_text
[SKIP]  web_content_id=12347  reason=orphaned_ai_turn_only
[WARN]  web_content_id=12348  reason=inferred_structure_no_labels  confidence=low
[ERROR] web_content_id=12349  reason=parse_exception  detail=malformed_unicode
```

Summary line at end of each batch:
```
Batch summary: {n_processed} processed, {n_pairs} pairs extracted, {n_skipped} skipped, {n_warnings} warnings
```

---

## Validation Cases (Unit Tests)

Cases use the real OpenEvidence structural pattern confirmed from live data.

### Case 1 — Single Q&A pair (standard)

**Input text**:
```
New Conversation Visits New Visit Calculators Collections ... Conversations See all ...
user@email.com Open Evidence has signed content agreements with NEJM, JAMA ...
Share New Conversation
What are the first-line treatments for psoriasis?
Finished thinking Analyzing query Searching published medical literature, guidelines, FDA, CDC, and more
Synthesizing relevant information Done
First-line treatments for psoriasis include topical corticosteroids, vitamin D analogues, and coal tar preparations...
References
1. Journal of Dermatology, 2024...
```

**Expected output**:
- `search_query = "What are the first-line treatments for psoriasis?"`
- `ai_response = "First-line treatments for psoriasis include topical corticosteroids, vitamin D analogues, and coal tar preparations..."`
- `search_query_id = {id}_1`, `ai_response_id = {id}_1`
- References section NOT included in `ai_response`

---

### Case 2 — Single Q&A with ad indicator (strip leading digit)

**Input text**:
```
... Share New Conversation 10
causes of belching
Finished thinking Analyzing query Searching ... Synthesizing relevant information Done
Belching is a common symptom with multiple potential causes...
Follow-Up Questions
Which patient populations are most at risk?
```

**Expected output**:
- `search_query = "causes of belching"` — digit `10` stripped
- `ai_response = "Belching is a common symptom with multiple potential causes..."`
- Follow-Up Questions section NOT included in `ai_response`

---

### Case 3 — Multiple Q&A pairs on one page

**Input text**:
```
... New Conversation 8
why is silver sulfadiazine topical contraindicated in infants under 2 months old?
Answered on February 18, 2026 Finished thinking ... Done
Silver sulfadiazine is contraindicated in infants under 2 months old because sulfonamide therapy increases the risk of kernicterus...
New
what are alternative prescription-only topical agents recommended for diaper dermatitis
Answered on February 18, 2026 Finished thinking ... Done
Low-potency topical corticosteroids (such as hydrocortisone 1%) and topical antifungals are the primary prescription-only agents...
References ...
```

**Expected output**:
- Row 1: `search_query = "why is silver sulfadiazine topical contraindicated in infants under 2 months old?"`, `search_query_id = {id}_1`, `ai_response_id = {id}_1`
- Row 2: `search_query = "what are alternative prescription-only topical agents recommended for diaper dermatitis"`, `search_query_id = {id}_2`, `ai_response_id = {id}_2`
- "New" UI button before second question is stripped (not part of query)
- "Answered on February 18, 2026" is metadata, not part of query

---

### Case 4 — Page captured mid-load (no response rendered)

**Input text**:
```
... New Conversation 10
belching from lung cancer or diaphragm issue
Analyzing query Analyzing query
```

**Expected output**:
- `search_query = "belching from lung cancer or diaphragm issue"`
- `ai_response = NULL`, `ai_response_id = NULL`
- Log: `[SKIP] web_content_id={id} reason=page_captured_mid_load`

---

### Case 5 — Dashboard / non-conversation page

**Input text**:
```
New Conversation Visits New Visit ... Conversations See all Severe Anemia ER Decision
Hemorrhoid Medication Names ANCA Vasculitis Neuropathy Risk ...
Open Evidence has signed content agreements with NEJM ...
New Visit 12 Deep Consult Role of family physicians in rare pediatric movement disorder diagnosis ...
```

**Expected output**:
- `search_query = NULL`, `ai_response = NULL`
- Log: `[SKIP] web_content_id={id} reason=no_conversation_detected`
- Note: This URL should have been excluded by the `/ask/[a-f0-9-]+` URL filter before reaching parsing

---

## References

- Schema: `dtaa/references/schema.md` (includes `web_contents` and `extracted_texts` tables)
- SQL guidelines: `dtaa/references/guidelines.md`
- Platform config: `references/medai_platforms.md` — **read this before every extraction run**
