# DTAA Database Schema Reference

## Database Configuration
- Engine: MySQL 8.0+ with InnoDB
- Character Set: utf8mb4 (case-insensitive string matching)
- Time Zone: All datetime fields stored in UTC

---

## Core Channel Tables

### `ads`
`id`(PK), `url`(TEXT), `web_content_id`(FK→web_contents.id, NULL=non-healthcare source), `created`(DATETIME), `user_id`(FK), `client_id`(FK), `redirect_url`(TEXT), `destination_url`(TEXT), `type`(ENUM: STATIC/DYNAMIC/SCREENSHOT/CANVAS/EMAIL), `is_valuable`(TINYINT), `llm_annotation_status`(ENUM: NEW/PROCESSING/PROCESSING_FAILED/PROCESSED/NOT_REQUIRED), `user_wave_id`(INT)

**Date column**: `created`
**Entity type in gpt_annotations**: `AD`

**`llm_annotation_status` semantics**:
- `NOT_REQUIRED` — set when the ad's `redirect_url` matches an active domain in `ad_ignorelist_domains`. Deliberate skip, not a failure. ~84% of ads each month; a stable share, not an anomaly.
- `NEW` — never sent to the LLM. For `type='EMAIL'` this is a permanent terminal state (see below), not a transient backlog.
- `PROCESSED` / `PROCESSING` / `PROCESSING_FAILED` — normal pipeline states.

**`type='EMAIL'` ads are never LLM-annotated**: zero rows in `gpt_annotations` for EMAIL-type ads across the entire table history (since 2022). They only ever sit in `NEW` or `NOT_REQUIRED`. OCR/keyword extraction *does* run for them — `extracted_texts` and `annotations` are populated normally via the `media` join. Only the `gpt_annotations` (LLM) step is missing. Exclude EMAIL-type ads from any SOV/Reach/Frequency query that depends on `gpt_annotations`, or the ads channel will silently undercount.

**LLM annotation coverage for ads starts ~Jan 2025**: ads captured before then are essentially absent from `gpt_annotations` (checked 2026-09: Nov 2024 had 1 annotated ad; brand-labelled monthly counts begin at 2025-01, with no backfill). Any brand trend that relies on the LLM label cannot see pre-2025 months — use URL/domain matching (`redirect_url` / `destination_url`) or the keyword `annotations` layer for those. The keyword layer is much looser than the LLM label (co-mentions, news pages): a month where the LLM label found ~26 Beyfortus ads had 45 keyword-matched ones.

### `ad_ignorelist_domains`
`id`(PK), `name`(VARCHAR — domain), `is_active`(TINYINT), `created`(DATETIME)

**Purpose**: Drives `ads.llm_annotation_status = 'NOT_REQUIRED'` — an ad whose `redirect_url` matches an active domain here is skipped by the annotation pipeline.
**Perf warning**: Do NOT verify this with `redirect_url LIKE CONCAT('%', d.name, '%')` — the non-sargable join times out even on a single day of ads.

### `web_contents`
`id`(PK), `user_id`(FK), `absolute_url`(TEXT), `duration`(TIME), `visited_timestamp`(DATETIME), `created`(DATETIME), `status`(ENUM), `type`(ENUM: WEB_PAGE/EMAIL_CAMPAIGN/AD_SOURCE_URL/HTML_WEB_PAGE/POST), `timezone`(VARCHAR), `closed_timestamp`(DATETIME), `tracked_url_id`(FK), `session`(INT), `client_id`(FK), `web_content_group_id`(FK), `user_wave_id`(INT)

**Mandatory filter**: `type IN ('WEB_PAGE', 'HTML_WEB_PAGE')`
**Date column**: `created`
**Annotation join path**: `web_contents.web_content_group_id` → `web_content_groups.id` → `gpt_annotations` (entity_type = `WEB_CONTENT_GROUP`)

### `extracted_texts`
`id`(PK), `entity_id`(INT), `entity_type`(ENUM: WEB_CONTENT/WEB_CONTENT_TITLE/MEDIA/POST_HEADER/POST_CONTENT/AD_SAFETY_INFO/WEB_CONTENT_DESCRIPTION/POST_ACCOUNT_NAME), `text`(MEDIUMTEXT), `status`(ENUM), `created`(DATETIME), `modified`(DATETIME)

**Join** (ads): `media.entity_id = ads.id AND media.entity_type = 'AD'`, then `extracted_texts.entity_id = media.id AND extracted_texts.entity_type = 'MEDIA'`

### `annotations` (keyword/OCR layer — distinct from `gpt_annotations`)
`id`(PK), `entity_id`(INT), `entity_type`(ENUM: same set as `extracted_texts`), `term`(VARCHAR), `root_name`(VARCHAR), `label`(VARCHAR), `term_frequency`(INT), `noise`(TINYINT), `created`(DATETIME), `modified`(DATETIME)

**Not the same as `gpt_annotations`**: this is the pre-LLM keyword/term extraction layer. An entity can have `annotations` rows while having no `gpt_annotations` row at all (this is exactly the case for EMAIL-type ads).
**Join** (ads): same `media` hop as `extracted_texts` above, with `entity_type = 'MEDIA'`.

**Join** (web contents): `extracted_texts.entity_id = web_contents.id AND extracted_texts.entity_type = 'WEB_CONTENT'`
**Purpose**: Raw text extracted from visited webpages; used for MedAI conversation extraction (`/dtaa-chat-extractor`)
**Note**: Uses the entity pattern (same as `gpt_annotations`) — NOT a `web_content_id` column. A web_content_id may have zero or one extracted_texts row. Use INNER JOIN to restrict to pages with extracted text.

### `emails`
`id`(PK), `web_content_id`(FK), `subject`(VARCHAR), `sender`(VARCHAR), `sender_email`(VARCHAR), `received_date`(DATETIME), `created`(DATETIME), `user_id`(FK), `client_id`(FK), `sender_category`(ENUM: MEDICAL_REPRESENTATIVE/MANUFACTURER/THIRD_PARTY_WEBSITE), `ad_embedded_email`(ENUM: UNKNOWN/YES/NO)

**Date column**: `received_date` (always use this, NOT `created`)
**Entity type in gpt_annotations**: `EMAIL`

**LLM annotation coverage for emails starts Jan 2025** (same cutover as ads): from 2025-01 onward ~100% of emails have a `gpt_annotations` row (checked 2026-09: 3,867/3,868 in Jan 2025; worst month Nov 2025 at 94%). Before that, coverage is near zero (7–21 annotated emails/month Aug–Nov 2024 against ~3–4k volume; Dec 2024: 147). Expect the current month to lag while the pipeline catches up. For brand identification prefer the LLM label — brands usually appear in the email body, so `subject`/`sender` LIKE-matching finds only a strict subset.

### `posts`
`id`(PK), `is_sponsored`(TINYINT), `redirect_url`(TEXT), `date`(DATETIME), `account_name`(VARCHAR), `urn`(VARCHAR), `created`/`modified`(DATETIME), `type`(TINYINT), `llm_annotation_status`(ENUM)

**No `is_valuable` column** — that exists only on `ads`.

**`type` codes** (source: `POST_TYPE_ENUM` in `perxcept-ap-server/src/app/entities/extn/post.entity.ts`, matched by domain in the extensions' `POST_TYPE` constant):

| code | platform | code | platform |
|---|---|---|---|
| 1 | Doximity | 4 | LinkedIn |
| 2 | Sermo | 5 | Twitter/X |
| 3 | Facebook | 6 | YouTube |

**Date column**: Join `web_content_posts` → `web_contents.created`
**User join path**: `posts.id` → `web_content_posts.post_id` → `web_contents.user_id`
**Entity type in gpt_annotations**: `POST`

### `search_results`
`id`(PK), `search_query_id`(FK), `title`(VARCHAR), `description`(TEXT), `redirect_url`(TEXT), `rank`(INT), `tracked_url_id`(FK), `created`(DATETIME), `is_branded`(TINYINT), `user_id`(FK), `client_id`(FK), `page_number`(INT), `type`(ENUM: SPONSORED_AD/ORGANIC/AI_REFERENCE), `is_clicked`(TINYINT)

**Type filters**: `SPONSORED_AD`=search ads, `ORGANIC`=organic results, `AI_REFERENCE`=AI response links
**Date column**: `created`
**Entity type in gpt_annotations**: always `SEARCH_RESULT`, for all three `type` values. `SEARCH_AD` is no longer written (0 rows for Sept 2026 sponsored ads).
**`is_healthcare_relevant` is NULL for every annotated `SPONSORED_AD`** (checked 2026-10: 4,806 annotated Sept 2026 search ads, all NULL; ORGANIC/AI_REFERENCE are populated 0/1). Do not use it to classify search ads as healthcare — use `therapeutic_area_id IS NOT NULL` or a `gpt_annotations_brands` row on the ad's annotation instead. Annotation coverage of search ads is also low (~14% of Sept 2026 sponsored results).

### `search_queries`
`id`(PK), `search_query`(VARCHAR), `is_branded`(TINYINT), `user_id`(FK), `client_id`(FK), `engine_type`(ENUM: BING/GOOGLE), `timezone`(VARCHAR), `timestamp`(DATETIME), `created`(DATETIME), `user_wave_id`(INT), `parent_query_id`(INT), `ai_mode_engaged`(TINYINT), `ai_mode_duration`(TIME), `is_show_more_clicked`(TINYINT)

**Entity type in gpt_annotations**: `SEARCH_QUERY`

### `ai_responses`
`id`(PK), `search_query_id`(INT), `response`(LONGTEXT), `response_type`(ENUM: OVERVIEW/AI_MODE), `llm_annotation_status`(ENUM)

---

## User & Project Tables

### `users`
`id`(PK), `npi`(INT), `allow_tracking`(TINYINT), `flags`(INT), `joined_date`(DATETIME), `zoomrx_user_id`(INT)

**PRIVACY**: Only `id` (as user_id) and `npi` (only if explicitly requested) may appear in SELECT. All other columns are FORBIDDEN.

### `clients`
`id`(PK), `user_id`(FK), `user_agent`(VARCHAR), `device_platform`(VARCHAR), `platform_version`(VARCHAR), `browser_platform`(VARCHAR), `browser_version`(VARCHAR), `last_request`(DATETIME), `app_version`(VARCHAR), `flags`(INT)

### `projects`
`id`(PK), `name`(VARCHAR)
**Alias**: "TL" (Target List) refers to project name

### `project_target_list`
`id`(PK), `project_id`(FK→projects.id), `npi`(INT)
**Used to**: Identify target HCPs/patients by NPI for SOV/Reach/Frequency analysis

---

## Annotation Tables

### `gpt_annotations` (central hub)
`id`(PK), `entity_id`(INT), `entity_type`(ENUM: AD/WEB_CONTENT_GROUP/EMAIL/SEARCH_RESULT/SEARCH_AD/POST), `is_healthcare_relevant`(TINYINT), `target_audience`(ENUM: PATIENT/HCP/UNKNOWN), `therapeutic_area_id`(FK)

**entity_type mapping**:
- `AD` → join `ads` on `entity_id = ads.id`
- `WEB_CONTENT_GROUP` → join `web_content_groups` on `entity_id = web_content_groups.id`
- `EMAIL` → join `emails` on `entity_id = emails.id`
- `SEARCH_RESULT` → join `search_results` (type=ORGANIC or AI_REFERENCE)
- `SEARCH_AD` → join `search_results` (type=SPONSORED_AD)
- `POST` → join `posts` on `entity_id = posts.id`

### Junction Tables
- **`gpt_annotations_brands`**: `gpt_annotation_id`(PK,FK), `brand_id`(PK,FK→brand_terms.id)
- **`gpt_annotations_diseases`**: `gpt_annotation_id`(PK,FK), `disease_id`(PK,FK→disease_terms.id)
  - No disease tagged = TA agnostic entity
- **`gpt_annotations_disease_brand_weights`**: `gpt_annotation_id`(FK), `disease_id`(FK), `brand_id`(FK), `weight`(DECIMAL, **0–100 percentage**)
  - The only brand/disease source for `WEB_CONTENT_GROUP` annotations (`gpt_annotations_brands` has 0 rows for that type). `gpt_annotations_diseases_brands` does not exist.
  - `weight` is a percent share of the page, not a 0–1 fraction: multiply by `weight / 100`. Per page, a brand's weight summed across its disease rows never exceeds 100 (verified 2026-10-13).
  - A page can list one brand under several diseases → several rows. Dedupe by `web_contents.id` before summing raw `duration`, or the time is double-counted.
  - **Used only for web contents** (Share of Attention calculations)
  - **Disease-only rows have `brand_id IS NULL`** — that is the disease weight of the page
    (e.g. "CLL 70%"). `gpt_annotations_diseases` has 0 rows for `WEB_CONTENT_GROUP`, so a
    disease filter on web pages must use `brand_id IS NULL AND weight > N` here (verified 2026-10-27
    on openevidence.com: 15.2k of 16.2k annotated 2026 visits have disease-only rows).
- **`gpt_annotations_manufacturers`**: `gpt_annotation_id`(PK,FK), `manufacturer_id`(PK,FK→manufacturer_terms.id)
- **`gpt_annotations_topics`**: `id`(PK), `gpt_annotation_id`(FK), `primary_topic`(ENUM), `secondary_topic`(ENUM), `primary_topic_detailed`(VARCHAR), `secondary_topic_detailed`(VARCHAR)
  - **"Unique ad campaigns"** = `GROUP BY primary_topic_detailed` with one sample ad per
    group (`MIN(ads.id)`). The topics live only in this child table — `gpt_annotations`
    itself has no topic columns. `primary_topic_detailed` is free-text LLM output, so
    near-duplicate wordings appear as separate rows; treat the distinct count as an
    upper bound on distinct creatives and cluster similar descriptions when reporting.

---

## Reference / Lookup Tables

- **`brand_terms`**: `id`(PK), `standard_name`(VARCHAR)
- **`disease_terms`**: `id`(PK), `standard_name`(VARCHAR)
- **`manufacturer_terms`**: `id`(PK), `standard_name`(VARCHAR)
- **`therapeutic_areas`**: `id`(PK), `name`(VARCHAR)
- **`tracked_urls`**: `id`(PK), `url`(VARCHAR), `category`(ENUM), `brand_id`(FK), `is_interested_domain`(TINYINT), `archived`(TINYINT)
- **`specialities`**: `id`(PK), `speciality`(VARCHAR)
- **`user_speciality_mappings`**: `id`(PK), `user_id`(FK), `speciality_id`(FK)
- **`web_content_groups`**: Groups web_contents by URL for annotation
- **`web_content_posts`**: `id`(PK), `post_id`(FK→posts.id), `web_content_id`(FK→web_contents.id)
- **`media`**: `id`(PK), `entity_id`(INT), `entity_type`(ENUM: POST/AD), `source_url`(TEXT)

---

## Key Relationships

### Ads ↔ Web Contents
- `ads.web_content_id` → `web_contents.id` (NULL = ad from non-healthcare site)

### Web Contents ↔ Annotations
- `web_contents.web_content_group_id` → `web_content_groups.id` → `gpt_annotations.entity_id` (entity_type='WEB_CONTENT_GROUP')

### Posts ↔ User/Date
- `posts.id` → `web_content_posts.post_id` → `web_content_posts.web_content_id` → `web_contents` (for user_id, created)

### Search Results ↔ Queries
- `search_results.search_query_id` → `search_queries.id`

### Target Users (SOV/Metrics)
- `project_target_list.npi` = `users.npi` → identifies which users belong to a project's target list

---

## Short-form messaging / sponsored clinical alerts (Medscape Brand Alerts etc.)

Native sponsored messages inside HCP platforms (Medscape Brand Alerts, Doximity
DocNews, Epocrates dashboards) are NOT a separate entity — they are captured, but
scattered across existing tables. Established 2026-09:

**Medscape Brand Alert — email arm** (the reliable capture):
- `emails` rows with `sender_email = 'Clinical_Update@mail.webmdprofessional.com'`
  (case-insensitive; ~45–60/mo, 100% gpt-annotated as EMAIL, so already in email SOV).
- The creative images land as `ads` rows with `type='EMAIL'` and
  `url LIKE '%medscapestatic.com%/EmailAlert/%'` — the URL path encodes
  `/EmailAlert/<Manufacturer>/<Brand>/...` (e.g. `Eli_Lilly/Jaypirca`). These EMAIL-type
  ads are never LLM-annotated (known gap), so filter by URL path, not annotations.
  Join back to the parent email via `ads.web_content_id = emails.web_content_id`.

**Medscape Brand Alert — on-site/web arm** (NOT systematically captured as ads):
- The Chrome extension's ad injector captures only **iframe-served** creatives
  (`content-injector.js` gates on `document.location.ancestorOrigins.length > 0`).
  Brand Alert units render **inline in the host page DOM** (native modules in the
  logged-in `/for-you` feed and article pages), so they never reach the `ads` table.
  The rare `ads` rows with `url LIKE '%img.medscapestatic.com/pi/alert/%'` are
  one-off iframe deliveries, not a reliable series.
- The unit **text IS captured** in `extracted_texts` (entity_type='WEB_CONTENT'):
  filter `text LIKE '%Information from Industry%'` on medscape pages — the label,
  headline, body and CTA of the native unit are all present. MDCalc sponsorships
  similarly show as `%sponsored by%` in page text. Full MHTML page snapshots live
  in GCS keyed by `web_content_id` (see perxcept-data-processing-service
  `processWeb.js`), so unit markup is recoverable retroactively.

**Medscape on-page selectors** (verified live 2026-09 on medscape.com article pages):
ad slots are `div[id^="ads-pos-"].AdUnit` (inside `.adswrapper`); sponsored native
units carry the label class **`.adlabelifi`** (CSS `::after` renders "Information
from Industry" — the label is CSS-generated, so it appears in innerText extraction
but as a class in markup), `.adlabelifg` = "Information from Government",
`.adlabelblank`/`.noAdLabel` = unlabeled; position 141 carries its label in a
`data-ad-text` attribute; plus `.sponsored-content-container`. Units only fill for
logged-in members.

**Doximity/Epocrates**: in-app delivery is not observed by DT. Only generic digest
emails (`support@doximity.com` DocNews) exist; sponsored arms are inside those, not
separable by sender.

**Caution**: a bare `%alert%` substring on ads URLs is noisy (internetalerts.org,
job-alert senders, mdalert.com) — always anchor on the medscapestatic paths or the
Clinical_Update sender.

## Session findings 2026-09 (IBD landscape pulls)

**Email sender classification**: `emails.sender_category` ∈ MANUFACTURER,
MEDICAL_REPRESENTATIVE, THIRD_PARTY_WEBSITE (plus NULL, ~2%). Use it for
manufacturer/rep/3rd-party splits; no separate lookup table needed.

**Ad creative text is NOT stored**: display ads have no OCR/copy text —
`extracted_texts` has no `entity_type='AD'` rows for banner ads and
`ads.google_annotations` is NULL on recent rows. The only message source is
`gpt_annotations_topics.primary_topic_detailed` (LLM description of the
creative). Paid-search creatives DO carry verbatim copy in
`search_results.title` and `search_results.description`, and the triggering
query text is `search_queries.search_query` via `search_results.search_query_id`.

**Query validator quirk**: the read tool rejects any statement containing the
keyword `REPLACE` (even the string function) as non-SELECT. Strip protocols
with nested `SUBSTRING_INDEX(url,'://',-1)` instead.

**User-level SOV in one scan** (avoids the 4×-replicated base-template timeout
on cross-brand pulls): aggregate per-item → per (user, brand) counts, then
`brand_items / SUM(brand_items) OVER (PARTITION BY user_id [, quarter])` and
sum per brand. Divide the summed user_sov by the universe N (distinct users in
the filtered channel, from a separate cheap COUNT) to reproduce
`AVG(individual_sov)` including zero-exposure users. Verified equal to the
skill formula on ads/search/email, Jan–Aug 2026.

**Presentation conventions confirmed by stakeholder review**: reach % uses the
active specialty panel as denominator (users with any channel activity in the
window), not the channel universe; per-user SOV, never pooled share of
exposures, for QoQ trends (pooled share overstated a 6-HCP/33-frequency Tremfya
blast as 63% vs 20% user-level); flag any channel with n<30 HCPs as low sample.
