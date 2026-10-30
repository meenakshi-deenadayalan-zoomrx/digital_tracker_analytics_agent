
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

Read `references/database.md` for query patterns and schema.

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

Read `references/selectors.md` for the inventory.

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

Read `references/ticketing.md` for the Remarkup template and priority mapping.
Use `dtsa_phabricator_create_task`.

See `references/service_map.json` for channel → implementation mapping.
See the Channel Reference section below for cross-repo flow links.

## Channel Reference

# Channel → Repository Documentation Reference

## web_contents (Page Visit Tracking)

### Chrome
- Entry: `app/background-scripts/background.js` → `chrome.webNavigation.onCommitted`
- Flow: Navigate → `isURLInTrackedDomains()` → `POST web_contents/add_webpage` → capture MHTML
- Docs: `digitrace-chrome-extension/docs/01-flows.md`, `docs/02-background-script.md`

### iOS
- Entry: `Resources/background-scripts/background.js` → `chrome.webNavigation.onCompleted`
- Flow: Navigate → A/B test branch → `delay(3000ms)` → `getWebContentAsMHTML` → `POST web_contents/add_webpage`
- Docs: `perxcept-ios/docs/01-flows.md`, `docs/02-background-script.md`

### macOS
- Entry: `script.js` → `pageLoaded` message → Swift `SafariExtensionHandler`
- Flow: `pageLoaded` → Swift routes → `getWebContent` msg → `POST web_contents/add_html_web_content`
- Docs: `perxcept-macos/docs/01-flows.md`, `docs/02-swift-layer.md`

### Backend
- Controller: `WebContentsController` → `POST /api_v2/web_contents/add_webpage`
- DB: `extn.web_contents` table
- Docs: `perxcept-ap-server/docs/03-extension-api.md`

---

## ads (Display Ad Tracking)

### Chrome
- Entry: `app/content-scripts/content.js` → MutationObserver + RxJS debounce
- Flow: Detect ad images → send `ads` message → background → `POST ads/`
- Docs: `digitrace-chrome-extension/docs/03-content-scripts.md`

### iOS
- Entry: `Resources/content-scripts/content.js` → `getImageURLs` message
- Docs: `perxcept-ios/docs/01-flows.md`

### macOS
- Entry: `script.js` → `sendADImages` message → Swift `RequestHandler.sendADImageURLs()`
- Docs: `perxcept-macos/docs/02-swift-layer.md`

### Backend
- Controller: `AdsController` → `POST /api_v2/ads/`
- DB: `extn.ads`, `extn.media`
- Data Processing: `process/extension/processImage.js` (Gemini OCR + Vision fallback)
- Docs: `perxcept-ap-server/docs/03-extension-api.md`, `perxcept-data-processing-service/docs/02-extension-pipeline.md`

### Known Failure Patterns
- Ad domain not in `extn.ad_server_domains` whitelist → ad rejected
- Destination URL in `extn.ad_ignorelist_domains` → status `NOT_REQUIRED`
- Safe-search (adult/violent) → status `NOT_REQUIRED`

---

## email (Email Content Tracking)

### Chrome
- Entry: `app/content-scripts/email-capture.js` → injected into Gmail/Yahoo/Outlook/AOL/Doximity
- Flow: Extract metadata + body → show preview modal → `POST web_contents/add_email_content`
- Docs: `digitrace-chrome-extension/docs/03-content-scripts.md`

### iOS
- Entry: `Resources/content-scripts/email-capture.js` → Gmail/Yahoo/Outlook/AOL
- Docs: `perxcept-ios/docs/01-flows.md`

### macOS
- Entry: `Resources/email-capture.js` → `sendEmail` msg → Swift `RequestHandler.sendEmailContent()`
- Docs: `perxcept-macos/docs/02-swift-layer.md`

### Backend
- Controller: `WebContentsController` → `POST /api_v2/web_contents/add_email_content`
- DB: `extn.web_contents`, `extn.emails`

---

## search_results (SERP Tracking)

### Chrome ONLY (not on iOS or macOS)
- Entry: `app/content-scripts/sponsoredAd-capture.js` → injected into google.com/search
- Captures: Organic results, paid ads, AI Overview, AI Mode responses
- Selectors: Server-overridable via `GET search-results/get_selectors` → stored in `GOOGLE_SELECTORS`
- Docs: `digitrace-chrome-extension/docs/03-content-scripts.md`

### macOS (search ads only)
- Entry: `script.js` → `sponsoredAds` message → Swift (only paid results, no organic/AI)

### Backend
- Controller: `SearchResultsController` → `POST /api_v2/search-results/`
- DB: `extn.search_queries`, `extn.search_results`, `extn.ai_responses`, `extn.search_ads`
- Data Processing: Medical filtering via GPT-4o-mini classification
- Docs: `perxcept-data-processing-service/docs/05-search-result-flow.md`

---

## social_posts (Social Post Tracking)

### Chrome
- Entry: `app/content-scripts/content.js` → social post detection on LinkedIn/Sermo/Doximity/Facebook/YouTube
- Flow: Detect post → send `posts` message → `POST web_contents/add_post`

### macOS
- Entry: `Resources/post-capture.js` → LinkedIn/Doximity/FB/Twitter/Sermo
- Flow: `sponsoredPosts` msg → Swift `RequestHandler.sendPostToServer()`

### iOS: Not supported

### Backend
- Controller: `WebContentsController` → `POST /api_v2/web_contents/add_post`
- DB: `extn.posts`, `extn.background_requests`

---

## Error Codes (All Platforms)

| Code | Meaning | Client Behavior |
|---|---|---|
| HTTP 420 | User tracking quota exceeded | Disable ALL tracking (`TRACKING_APPROVED=0` / `ALLOW_TRACKING=false`) |
| HTTP 461 | Module-specific quota exceeded | Disable that specific module |
| HTTP 403 + `PEUD-403` | User account disabled | Set `IS_USER_DISABLED=true` (macOS only) |
