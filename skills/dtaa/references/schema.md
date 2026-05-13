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

### `web_contents`
`id`(PK), `user_id`(FK), `absolute_url`(TEXT), `duration`(TIME), `visited_timestamp`(DATETIME), `created`(DATETIME), `status`(ENUM), `type`(ENUM: WEB_PAGE/EMAIL_CAMPAIGN/AD_SOURCE_URL/HTML_WEB_PAGE/POST), `timezone`(VARCHAR), `closed_timestamp`(DATETIME), `tracked_url_id`(FK), `session`(INT), `client_id`(FK), `web_content_group_id`(FK), `user_wave_id`(INT)

**Mandatory filter**: `type IN ('WEB_PAGE', 'HTML_WEB_PAGE')`
**Date column**: `created`
**Annotation join path**: `web_contents.web_content_group_id` → `web_content_groups.id` → `gpt_annotations` (entity_type = `WEB_CONTENT_GROUP`)

### `emails`
`id`(PK), `web_content_id`(FK), `subject`(VARCHAR), `sender`(VARCHAR), `sender_email`(VARCHAR), `received_date`(DATETIME), `created`(DATETIME), `user_id`(FK), `client_id`(FK), `sender_category`(ENUM: MEDICAL_REPRESENTATIVE/MANUFACTURER/THIRD_PARTY_WEBSITE), `ad_embedded_email`(ENUM: UNKNOWN/YES/NO)

**Date column**: `received_date` (always use this, NOT `created`)
**Entity type in gpt_annotations**: `EMAIL`

### `posts`
`id`(PK), `redirect_url`(TEXT), `account_name`(VARCHAR), `type`(TINYINT), `llm_annotation_status`(ENUM)

**Date column**: Join `web_content_posts` → `web_contents.created`
**User join path**: `posts.id` → `web_content_posts.post_id` → `web_contents.user_id`
**Entity type in gpt_annotations**: `POST`

### `search_results`
`id`(PK), `search_query_id`(FK), `title`(VARCHAR), `description`(TEXT), `redirect_url`(TEXT), `rank`(INT), `tracked_url_id`(FK), `created`(DATETIME), `is_branded`(TINYINT), `user_id`(FK), `client_id`(FK), `page_number`(INT), `type`(ENUM: SPONSORED_AD/ORGANIC/AI_REFERENCE), `is_clicked`(TINYINT)

**Type filters**: `SPONSORED_AD`=search ads, `ORGANIC`=organic results, `AI_REFERENCE`=AI response links
**Date column**: `created`
**Entity type in gpt_annotations**: `SEARCH_AD` (SPONSORED_AD) or `SEARCH_RESULT` (ORGANIC/AI_REFERENCE)

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
- **`gpt_annotations_diseases_brands`**: `gpt_annotation_id`(PK,FK), `disease_id`(PK,FK), `brand_id`(PK,FK), `weight`(DECIMAL)
  - **Used only for web contents** (Share of Attention calculations)
- **`gpt_annotations_manufacturers`**: `gpt_annotation_id`(PK,FK), `manufacturer_id`(PK,FK→manufacturer_terms.id)
- **`gpt_annotations_topics`**: `id`(PK), `gpt_annotation_id`(FK), `primary_topic`(ENUM), `secondary_topic`(ENUM), `primary_topic_detailed`(VARCHAR), `secondary_topic_detailed`(VARCHAR)

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
