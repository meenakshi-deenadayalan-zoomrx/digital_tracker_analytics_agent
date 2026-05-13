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
