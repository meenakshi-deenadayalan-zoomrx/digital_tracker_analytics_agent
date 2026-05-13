# Selector Inventory by Channel

## Email Selectors

### Gmail
| Element | CSS Selector | Notes |
|---|---|---|
| Subject | `h2.hP` | Primary — most likely to break on Gmail redesign |
| Body | `div.a3s.aiL` | Main readable body container |
| From address | `span.gD` | Sender email address |

Test URL: `https://mail.google.com`

### Yahoo Mail
| Element | CSS Selector |
|---|---|
| Subject | `[data-test-id='message-subject']` |
| Body | `[data-test-id='message-view-body']` |

### Outlook (outlook.com)
| Element | CSS Selector |
|---|---|
| Body | `[aria-label*='Message body']` |
| Alternative body | `div.allowTextSelection` |

### AOL Mail
| Element | CSS Selector |
|---|---|
| Subject | `[data-test-id='message-subject']` |
| Body | `[data-test-id='message-view-body']` |

### Doximity (email channel)
Email selectors are embedded in `email-capture.js`. Use `dtsa_grep_repo` to find current selectors.

---

## Search Result Selectors (Chrome only)

Google SERP selectors are **server-overridable** via `GET /api_v2/search-results/get_selectors`.
The live selectors are stored in the `GOOGLE_SELECTORS` Chrome storage key — they may differ from what's hardcoded.

To check what selectors are currently active for a user, query:
```sql
SELECT DATE(created_at) AS dt, COUNT(*) AS cnt
FROM audit_logs
WHERE event LIKE '%selector%'
  AND created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY dt;
```

Hardcoded fallback selectors are in `sponsoredAd-capture.js`. Use `dtsa_grep_repo` to find them.

Test URL: `https://www.google.com/search?q=test`

---

## Social Post Selectors

Social post detection is platform-specific and hardcoded in content scripts.
These change frequently due to platform updates.

| Platform | Detection Method | Chrome File |
|---|---|---|
| LinkedIn | Post container + author elements | `content.js` |
| Sermo | Custom forum post structure | `content.js` |
| Doximity | Article/post elements | `content.js` |
| Facebook | Post container, sponsored label | `content.js` |
| YouTube | Video metadata extraction | `content.js` |
| Twitter/X | Post elements | `post-capture.js` (macOS only) |

To find current selectors: `dtsa_grep_repo(repo, "linkedin|sermo|doximity")`

> Social_posts volume drops for a single platform = DOM restructure on that platform. Most likely cause.

---

## Ad Selectors

Ad detection uses MutationObserver + image URL matching, not CSS selectors.
Failures here are usually:
1. Image URL domain not in `ad_server_domains` whitelist → check DB table
2. Destination URL in `ad_ignorelist_domains` blacklist → check DB table
3. MutationObserver detached on SPA navigation

Use `dtsa_playwright_selector` to verify ad images are present on a known ad-heavy page,
then cross-reference with `ad_server_domains` via `dtsa_mysql_read`.
