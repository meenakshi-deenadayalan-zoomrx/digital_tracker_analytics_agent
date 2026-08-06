# Supported MedAI Platforms

This file is the authoritative source for MedAI platform configurations.
The Chat Extractor skill reads this file at runtime — do NOT hardcode platform domains in SKILL.md.

---

## How to Add a New Platform

1. Copy an existing platform block below
2. Fill in all fields: domain, display_name, conversation_url_regexp, extraction_pattern, noise_anchors, notes
3. Append the domain's `conversation_url_regexp` to the Combined REGEXP section
4. Reinstall the skill: `cp -r skills/dtaa-chat-extractor ~/.claude/skills/`

---

## Platforms

### OpenEvidence
- **Domain**: `openevidence.com`
- **Display name**: OpenEvidence
- **Conversation URL REGEXP** (targets actual Q&A pages, not dashboard): `openevidence\.com/ask/[a-f0-9-]+`
- **Extraction pattern**: Structural (no explicit You:/AI: labels — see below)
- **Question anchor — start**: `New Conversation` or `Share New Conversation`, optionally followed by a single digit (1–10) which is an ad indicator and must be stripped
- **Question anchor — end**: `Finished thinking` or `Analyzing query` or `Answered on`
- **Answer anchor — start**: `Done` (appears after `Synthesizing relevant information`)
- **Answer anchor — end**: `References` or `Follow-Up Questions` or `Would you like me` or `Inbox`
- **Ad indicator**: A lone digit (1–10) between the question anchor and the question text — strip it from the extracted query
- **Noise anchors to ignore**: `New Conversation Visits New Visit Calculators Collections Dotflows Tools Messaging Fax Favorites`, `Conversations See all`, `Open Evidence has signed content agreements`, `Advertising helps keep OpenEvidence free for HCPs`
- **Multi-turn behavior**: Sequential — each additional exchange repeats the full pattern `[question anchor] → [question] → [thinking anchors] → Done → [response] → [end anchor]`. Count each repeat as a new pair.
- **Mid-load pages**: If `Finished thinking` / `Analyzing query` appears but `Done` does not → page captured before response rendered → `ai_response = NULL`
- **Notes**:
  - Dashboard pages (`openevidence.com/` and `/ask` without UUID) contain only conversation title lists, not Q&A content — excluded by the conversation URL REGEXP
  - `Answered on [date]` before the thinking anchors means a previously-answered question is being reviewed; the date is metadata, not part of the question
  - Sidebar lists past conversation titles (e.g., "Causes of Belching", "Tremfya Appeal") — these are noise, not the current question

---

## Combined URL REGEXP (SQL)

When filtering webpages by platform, join all per-platform `conversation_url_regexp` values with `|`:

```
openevidence\.com/ask/[a-f0-9-]+
```

Update this section whenever a new platform is added. This is what gets inserted into the SQL WHERE clause:

```sql
AND wc.absolute_url REGEXP 'openevidence\\.com/ask/[a-f0-9-]+'
```

---

## Platform Field Reference

| Field | Description |
|---|---|
| `Domain` | Bare domain used for display and documentation |
| `Conversation URL REGEXP` | MySQL-safe REGEXP targeting only actual Q&A pages (not dashboards or nav pages) |
| `Extraction pattern` | `structural` (anchor-based) or `labeled` (explicit You:/AI: markers) |
| `Question anchor — start` | Text pattern that precedes the question |
| `Question anchor — end` | Text pattern that follows the question (precedes AI thinking) |
| `Answer anchor — start` | Text pattern that precedes the AI response |
| `Answer anchor — end` | Text pattern that follows the AI response |
| `Ad indicator` | UI element injected near questions that must be stripped |
| `Noise anchors` | Navigation / chrome text to ignore before parsing |
| `Multi-turn behavior` | How additional Q&A rounds are structured on the same page |
| `Mid-load pages` | What the text looks like when the page was captured before rendering finished |
| `Notes` | Platform-specific edge cases or parsing quirks |
