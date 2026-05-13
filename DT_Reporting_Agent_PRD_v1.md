# DT Reporting Agent — Product Requirements Document v1.0

**Date:** 2026-04-13  
**Author:** Meenakshi Deenadayalan (with Claude)  
**Status:** Ready for Engineering Review  
**Stakeholder:** Manoj

---

## 1. Overview

### 1.1 What We Are Building

The **DT Reporting Agent** is a portal-based pipeline that takes a project name as input and produces a complete, report-ready package: QC'd data tables, aggregated Excel workbooks, a populated PowerPoint deck, and (optionally) a narrative draft. Every number the agent produces is cited to its source.

### 1.2 Goal

A consultant selects a project, defines waves, downloads raw data for QC, uploads corrections, and generates the final report — no SQL, no manual Excel, no manual chart-building.

### 1.3 Long-Term Vision

A prospect requests a Digital Landscape Assessment → the agent delivers a sample report in 24 hours, zero consulting hours.

---

## 2. User Flow

```
┌─────────────────────────────────────────────────────────┐
│  1. PROJECT SETUP                                       │
│     Consultant creates project in admin portal:         │
│     - Project name, client                              │
│     - Market basket (brands, diseases, manufacturers)   │
│     - Channels to track                                 │
│     - Target list (NPIs)                                │
│     - Wave definitions (# of waves, date ranges)        │
├─────────────────────────────────────────────────────────┤
│  2. DATA PULL                                           │
│     Consultant selects project → system queries DB      │
│     for all channels, all waves                         │
├─────────────────────────────────────────────────────────┤
│  3. QC DOWNLOAD                                         │
│     Consultant downloads entity-level raw data with     │
│     brand/disease mappings from gpt_annotations         │
│     (per channel: ad-ID, email-ID, web_content-ID, etc.)│
├─────────────────────────────────────────────────────────┤
│  4. QC REVIEW (offline)                                 │
│     Consultant reviews, corrects wrong brand/disease    │
│     mappings in downloaded file                         │
├─────────────────────────────────────────────────────────┤
│  5. QC UPLOAD                                           │
│     Consultant uploads corrections → stored in          │
│     project-level QC override tables                    │
├─────────────────────────────────────────────────────────┤
│  6. REPORT GENERATION                                   │
│     Same selections → system JOINs source data with     │
│     QC corrections → runs aggregations → produces       │
│     PPT deck + Excel workbook                           │
├─────────────────────────────────────────────────────────┤
│  7. DOWNLOAD / EMAIL                                    │
│     Consultant downloads PPT + Excel from portal        │
│     (or receives via email if generation > 1 min)       │
│     Past runs are stored and retrievable per project    │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Interface

- **Platform:** Separate admin portal (existing PERxCEPT admin portal, screenshot provided)
- **Style:** Form-based workflow, NOT a chat agent
- **No LLM orchestration** for the core pipeline (Tools 1–3). Claude is used only for Tool 4 (narrative generation)
- **Authentication:** Uses existing portal login system
- **Access Control:** Product team vs. Consulting team — use existing role definitions in the portal

---

## 4. Database

### 4.1 Database Type

**MySQL** (existing PERxCEPT/Digital Tracker database)

### 4.2 Project Details Table (NEW — must be created)

This table is the single source of truth for all project configuration. Tool 1 reads from it instead of hardcoding values.

```sql
CREATE TABLE project_details (
    id INT PRIMARY KEY AUTO_INCREMENT,
    project_name VARCHAR(255) NOT NULL,
    client_id INT NOT NULL,
    -- Market basket
    brands JSON NOT NULL,          -- e.g., ["Calquence","Brukinsa","Venclexta","Imbruvica","Jaypirca"]
    diseases JSON NOT NULL,        -- e.g., ["CLL","SLL"]
    manufacturers JSON,            -- e.g., ["AstraZeneca","BeiGene","AbbVie","J&J","Lilly"]
    -- Channels
    channels JSON NOT NULL,        -- e.g., ["AD","EMAIL","SEARCH_RESULT","WEB_CONTENT","POST","AI_RESPONSE"]
    -- Wave definitions
    num_waves INT NOT NULL DEFAULT 1,
    wave_definitions JSON NOT NULL, -- e.g., [{"wave":1,"start":"2024-07-01","end":"2024-09-30"},{"wave":2,"start":"2024-10-01","end":"2024-12-31"}]
    -- Target list link
    -- Uses existing project_target_list table (project_id FK)
    -- Metadata
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    status ENUM('ACTIVE','ARCHIVED') DEFAULT 'ACTIVE'
);
```

### 4.3 Existing Channel Tables

Separate tables per channel (all join to `gpt_annotations` for brand/disease):

| Channel | Table | Date Column | Entity Type(s) in annotations |
|---|---|---|---|
| Ads (banner/display) | `ads` | `created` (fallback from `web_contents.visited_timestamp`) | `'AD'`, `'AD_SAFETY_INFO'`, `'MEDIA'` |
| Emails | `emails` | `received_date` | `'EMAIL'` |
| Search Results | `search_results` | varies | `'SEARCH_AD'`, `'SEARCH_RESULT'` |
| Web Content | `web_contents` | `visited_timestamp` | `'WEB_CONTENT_GROUP'` |
| Posts (Social) | `posts` (via `web_content_posts` → `web_contents`) | from `web_contents` | `'POST'` |
| AI Responses | `ai_responses` | varies | varies |

### 4.4 Annotation Tables

- **`gpt_annotations`** — central hub for brand/disease/manufacturer tagging
- Junction tables: `gpt_annotations_diseases_brands` (includes `weight` for multi-brand pages)
- Brand resolution: `root_name` in annotations, filtered by `label = 'Brand'` or `'Disease'`

### 4.5 QC Tables (EXISTING — created by engineering team)

Engineering has already created **channel-specific QC tables**, which is the correct approach. Each table has typed columns specific to that entity's QC needs, proper foreign keys to source tables, and clean JOINs at query time.

#### Existing QC Tables

| Table | Purpose | Key QC Fields |
|---|---|---|
| `report_qc_web_contents` | Correct brand/disease/category on web browsing data | brand, disease, website_category, healthcare_relevance |
| `report_qc_email_senders` | Correct email sender categorization | sender_name, sender_category (manufacturer/rep/third-party) |
| `report_qc_indications_diseases` | Correct disease/indication mappings | indication, disease, sub_indication |
| `report_qc_manufacturers` | Correct manufacturer attribution | manufacturer_name, parent_company |
| `report_qc_search_queries` | Correct search query classification | query_type (branded/unbranded), target_audience (HCP/patient) |
| `report_qc_topics` | Correct content topic/messaging classification | topic (efficacy, safety, access, dosing, etc.) |
| `report_qc_trial_names` | Standardize clinical trial name references | trial_name, trial_id |
| `report_qc_brands` | Correct brand name mappings | brand_name, generic_name |

#### Why channel-specific tables (not a single generic `qc_overrides` table):

1. **Typed columns** — each entity type has different correctable fields (email sender category vs. web content category vs. search query type). Typed columns enforce data integrity that a generic `field_name`/`value` string pair cannot.
2. **Query performance** — at report generation, each channel query directly JOINs its own QC table with a clean single LEFT JOIN, instead of multiple self-JOINs on a generic table filtered by `entity_type` + `field_name`.
3. **Referential integrity** — each QC table can have proper FKs to its source table (e.g., `report_qc_web_contents.web_content_id → web_contents.id`).
4. **Mirrors the QC workflow** — consultants QC by channel (download ads → fix brands; download emails → fix senders). Separate tables match this naturally.

#### Behavior:
- Second correction to same record **overwrites** the first (UNIQUE constraint on project + entity_id)
- At query time, Tool 1 LEFT JOINs the appropriate QC table and uses `COALESCE(qc.corrected_value, gpt.root_name)` to prefer corrected values
- History is not kept (latest correction wins)

### 4.6 Report Runs Table (NEW — for retrievability)

```sql
CREATE TABLE report_runs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    wave_definitions JSON NOT NULL,
    generated_by INT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ppt_file_path VARCHAR(500),
    excel_file_path VARCHAR(500),
    status ENUM('GENERATING','COMPLETED','FAILED','EMAILED') DEFAULT 'GENERATING',
    FOREIGN KEY (project_id) REFERENCES project_details(id)
);
```

---

## 5. Tool Specifications

### 5.1 Tool 1 — `query_project_data`

**Purpose:** Load project config from DB, query all specified channels, return raw and aggregated data with full metadata.

**Input:**
- `project_name` (string) — looked up in `project_details`
- Consultant confirms echoed config before proceeding

**Process:**
1. Read project config from `project_details` (brands, diseases, channels, wave_definitions, target NPIs)
2. For each channel in `channels`:
   - Query the channel table
   - JOIN to `gpt_annotations` for brand/disease
   - LEFT JOIN the appropriate channel-specific QC table (e.g., `report_qc_web_contents` for web data, `report_qc_email_senders` for emails) for corrections
   - Filter by: `project_target_list` (NPIs), wave date ranges, mandatory quality filters (from DTAA guidelines: user quality filter, survey response filter, `is_healthcare_relevant`)
   - Exclude test users (speciality_id NOT IN (28, 29, 30, 32))
3. For web content: compute session-level metrics (20-min gap = new session, partitioned by user)
4. Return raw entity-level data per channel with: entity ID, user_id, brand, disease, date, wave_number, all content fields

**Output:**
```json
{
  "project_config": { /* echoed for confirmation */ },
  "data_freshness": "2026-04-12T23:45:00Z",
  "channels": {
    "AD": { "raw_count": 1245, "data": [...] },
    "EMAIL": { "raw_count": 340, "data": [...] },
    ...
  }
}
```

**Guardrails:**
- Every record has: source table + query parameters + date range + wave number
- Agent echoes full project config; consultant confirms before output
- Data freshness shown at session start; warning if data >7 days old
- Agent cannot produce a metric not in source data → outputs `[NOT IN DATA]`

### 5.2 Tool 2 — `aggregate_and_test`

**Purpose:** Take raw data, apply metric calculations and significance testing, return slide-ready tables.

#### 5.2.1 Core Metrics

All share metrics use the **average-of-individual-HCP-shares methodology** (not overall weighted average), as confirmed across all three sample reports (Gilead p.89, Exelixis p.8).

| Metric | Definition | Channels | Formula |
|---|---|---|---|
| **SOV / Share of Exposure** | Average per-HCP share of branded content | Ads, Emails, Search, Posts | For each HCP: (brand exposures / total market basket exposures). SOV = mean across all HCPs |
| **Share of Attention** | Time-weighted brand exposure | Web Content | For each HCP: (brand_mentions / total_mentions) × time_on_page, summed per brand. Share = mean across HCPs |
| **Reach** | % of HCPs exposed to brand | All | (# unique HCPs with brand exposure / total panel HCPs) × 100 |
| **Frequency** | Avg exposures per reached HCP | All | (total brand exposures) / (# unique HCPs with brand exposure) |
| **Avg Time Spent** | Minutes browsing brand content per HCP | Web Content | Sum of weighted time per brand / # HCPs with brand encounters |

#### 5.2.2 Additional Metrics (from sample reports)

| Metric | Description |
|---|---|
| **Attention Funnel** | Healthcare → TA → Indication → Market Basket browsing (% time, reach, avg time/HCP at each level) |
| **Browsing by Website Category** | % time on journals, manufacturer sites, social networks, professional orgs, news, institutions |
| **Product Website User Journey** | Source (paid search, organic, direct, display ads, emails) → product site → destination |
| **Product Website Topic Engagement** | % time on: homepage, efficacy, dosing, safety, support, clinical data, MoA |
| **Paid Search Rank Distribution** | % of ads at Rank 1, 2, 3, 4+ per brand |
| **Paid Search SoE by Query Type** | Branded, unbranded, general TA terms, competitor terms |
| **Counter-Advertising** | Competitor ads appearing on own brand searches (and vice versa) |
| **Ad Placement** | Endemic vs. non-endemic website split, by brand |
| **Campaign-Level Metrics** | Unique campaigns, reach, frequency, impressions per campaign |
| **Email by Sender Type** | Manufacturer, rep, third-party split |
| **Email by Topic** | Insurance/access, efficacy, safety, clinical trial, dosing, general info |
| **Social Media by Platform** | Sermo, LinkedIn, YouTube, FB/Insta, Twitter/X — reach and exposure |
| **Brand Messaging Summary** | Key messaging themes by brand (HCP-targeted vs patient-targeted) |

#### 5.2.3 Aggregation Levels

- **Primary:** Brand-level (always)
- **Secondary (2D breakdowns, optional per slide):**
  - Brand × Website Category
  - Brand × Sender Type
  - Brand × Platform
  - Brand × Search Query Type
  - Brand × Ad Rank
  - Brand × Wave (for multi-wave trended views)

#### 5.2.4 Multi-Wave Support

- Waves stored as `wave_number`, `start_date`, `end_date` in project config
- Multi-wave reports show **all wave values side by side** (confirmed from sample reports: Pfizer deck shows QoQ trends, Exelixis shows Q3/Q4/Q1 side by side)
- If a wave has no data → show blank column with footnote "No data available for Wave N"

#### 5.2.5 Significance Testing

| Parameter | Standard |
|---|---|
| **Confidence level** | 95% (default across all projects) |
| **Test for share metrics (SOV)** | Z-test for proportions (pairwise: Brand A vs each competitor) |
| **Test for rate metrics (frequency)** | Independent samples t-test |
| **Multiple comparisons** | No correction (consistent with sample reports — pairwise flags only) |
| **Minimum n-size** | 30 HCPs. Below 30: suppress significance test, add "Low sample size" footnote |
| **Channel variation** | Same standard across all channels |
| **Output format** | Every significance flag includes: test used, confidence level, n-size, denominator. Missing = schema error |
| **Visual indicator** | "S" icon (as in Gilead report) or colored symbol per ZoomRx convention |

### 5.3 Tool 3 — `generate_ppt`

**Purpose:** Take aggregated tables, produce a populated PowerPoint deck using the standard ZoomRx slide structure.

#### 5.3.1 Deck Structure (derived from 3 sample reports)

The standard DT report follows this structure. Slides are parameterized by indication/channel:

| Section | Slide Types | Data Source |
|---|---|---|
| **01 — Introduction** | Digital Tracker Overview, Methodology, Respondent Profile (panel size, specialty, tier, device, practice setting) | Panel metadata + project config |
| **02 — Executive Summary** | Performance Scorecard (all channels at a glance), Key Findings (bullet points), Implications/Recommendations | Aggregated metrics across all channels |
| **03 — Digital Media Landscape** | | |
| *Brand Engagement* | Attention Funnel, Share of Attention bubble chart (Reach × Frequency × SoA), Top Websites by SoA, Browsing by Website Category, Product Website User Journey, Product Website Topic Engagement | Web content metrics |
| *Paid Search* | Reach/Frequency/SoE summary, SoE by Query Type, Paid Search Rank Distribution, Counter-Advertising, Search Terms Table | Search metrics |
| *Banner Ads / Social Media* | Ad SOE pie chart, Host Site breakdown (endemic vs non-endemic), Campaign-level metrics, FB/Insta campaign summary, Twitter/X posts, Platform-level exposure summary | Ad + social metrics |
| *Sponsored Emails* | Reach/Frequency/Share, Sender type breakdown, Topic analysis, Top email subject lines, Sample emails | Email metrics |
| **04 — Brand Messaging** | Key Messaging Themes per brand, Sample creative (HCP vs Patient targeted) | Ad/email content analysis |
| **05 — Appendix** | Methodology, Glossary, Detailed breakdowns, Search keywords lists | Reference data |

#### 5.3.2 Chart Types Used

| Chart Type | Where Used |
|---|---|
| Pie/Donut chart | SOV/SoE distribution, email brand distribution |
| Stacked bar (horizontal) | Paid search rank distribution, email sender type |
| Stacked bar (vertical) | Browsing by website category (per brand, per wave) |
| Bubble chart | Top websites (x=Reach, y=Frequency, size=SoA) |
| Line chart | Reach trends across waves |
| Bar chart | Avg time spent per brand, frequency per brand |
| Table/Scorecard | Performance scorecard, search terms, host site breakdowns |
| Sankey/Alluvial | Product website user journey (source → site → destination) |
| Funnel | Attention funnel (healthcare → TA → indication → market basket) |

#### 5.3.3 Template & Client Customization

- **Base template:** Standard ZoomRx DT template (.pptx file to be provided by design team)
- **Client templates:** One-time mapping where consultant matches ZoomRx slide IDs to client's branded layout
- **If unmapped slides exist:** Agent lists unmapped slides and stops until resolved

#### 5.3.4 Significance Visual Indicators

- "S" icon next to the metric value (as in Gilead report)
- Footnote: "S Denotes statistically significant difference with 95% confidence interval between [Brand] and competitors"
- "Low sample size" footnote with asterisk (*) when n < 30

#### 5.3.5 Wave Variants

- **Single-wave:** One quarter's data (e.g., "Q3'25")
- **Multi-wave:** Side-by-side columns per wave, with QoQ trend indicators
- Agent reads `wave_definitions` from project config and determines mode automatically

### 5.4 Tool 4 — `generate_narrative` (Phase 2 — Claude-powered)

**Purpose:** Take aggregated tables, produce executive summary, section-level talking points, and tactical implications.

**LLM:** Claude (Anthropic) — used only for this tool

**Output:**
- Executive summary (3-5 bullet points per section: HCP Browsing, Digital Media Landscape, Key Findings)
- Implications/Recommendations (per channel: Insight + Recommendation format, as in Exelixis p.19-20)
- Every claim cited to a source row. No causal assertions. No uncited external context.
- External context requires `[EXTERNAL: source]` tag

**Guardrails:**
- Cannot produce a metric not in source data
- Every claim must reference the specific metric, channel, and wave
- No fabricated numbers — outputs `[VERIFY]` if uncertain
- Narrative tone: direct, consultant-facing, uses DT terminology

---

## 6. Structural Guardrails

| Rule | Enforcement |
|---|---|
| Every metric in output has: source table + query parameters + date range | Schema validation — missing = error |
| Agent cannot produce a metric not in source data | Outputs `[NOT IN DATA]` instead |
| Agent echoes full project config; consultant confirms before generating | UI confirmation step required |
| Significance flag requires: test + confidence level + n-size + denominator | Schema validation — missing = error |
| External context requires `[EXTERNAL: source]` tag | Schema validation — missing = error |
| Data freshness shown at session start | Warning if data >7 days old |
| QC corrections override source annotations | LEFT JOIN channel-specific QC tables (e.g., `report_qc_web_contents`) with COALESCE at query time |

---

## 7. Failure Modes

| Failure Mode | Prevention |
|---|---|
| Wrong project config | Agent echoes config, consultant confirms before output |
| Fabricated metric | Schema: every metric requires source citation |
| Wrong significance threshold | Agent shows standard applied (95% CI); PO approves once per project |
| Wrong wave variant | Agent reads `wave_definitions` from config; states mode before generating |
| Unmapped client template | Agent lists unmapped slides, stops until resolved |
| Stale data | Agent shows data freshness timestamp; warns if >7 days |
| External context hallucination | Schema: `[EXTERNAL: source]` required (Tool 4 only) |
| Wrong brand/disease from GPT annotations | QC step: download, review, upload corrections before report generation |
| QC corrections not applied | System always JOINs channel-specific QC tables (e.g., `report_qc_web_contents`) at query time; verified in data pull step |
| Low sample size misleading results | Suppress significance below n=30; add "*Low sample size" footnote |
| Wave with no data | Show blank column with "No data available" footnote |
| Report generation timeout | If >1 min, email completed files to user; store in `report_runs` |

---

## 8. Acceptance Criteria

| Capability | Pass Criterion |
|---|---|
| Data accuracy | 0 discrepancies vs. manual SQL pull on 3 historical projects |
| QC override accuracy | Corrected values appear in all aggregated metrics and PPT output |
| Significance accuracy | ≥95% match with senior consultant manual review |
| PPT quality | ≥80% of slides need zero calculation corrections |
| Metric completeness | All metrics from sample reports (Pfizer, Gilead, Exelixis) are computable |
| Multi-wave support | Side-by-side wave display matches manual reports |
| Narrative quality (Tool 4) | ≥70% rated "usable as first draft" in blind review |
| Citation integrity | 100% of metrics have source citations (automated validation) |
| Report retrievability | Past runs retrievable by project with correct files |
| Performance | Report generation completes within 5 minutes for standard project |

---

## 9. Industry Averages (Section I — Deferred)

**Current status:** No IA benchmark table exists in the DB today.

**How IA is currently calculated:** Manually — consultants average metrics (e.g., SOV) across all projects in the same indication from the past 12 months.

**Recommendation for Phase 2:**
- Create an `ia_benchmarks` table: `indication`, `channel`, `metric`, `value`, `n_projects`, `date_range`, `computed_at`
- Scope: Same indication, same channel type
- Refresh: Quarterly (automated job that averages across all projects in indication)
- Agent pulls from this table and shows IA comparison alongside project metrics

---

## 10. Output Delivery

- **Primary:** Direct browser download from portal (PPT + Excel)
- **Fallback:** If generation > 1 minute, email completed files to user
- **Storage:** Files stored on server, associated with project via `report_runs` table
- **Retrievability:** Past runs visible in portal, downloadable at any time

---

## 11. Technical Architecture

```
┌────────────────────────────────────────────────────┐
│                 ADMIN PORTAL (UI)                    │
│  Project Setup │ QC Download │ QC Upload │ Generate  │
└────────────┬───────────────────────────┬────────────┘
             │                           │
             ▼                           ▼
┌────────────────────┐    ┌──────────────────────────┐
│   Tool 1            │    │   QC Service              │
│   query_project_    │    │   - Upload CSV            │
│   data              │    │   - Store in channel-     │
│   - MySQL queries   │    │     specific QC tables    │
│   - JOIN QC tables  │    │   - Validate format       │
│   - Return raw data │    └──────────────────────────┘
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│   Tool 2            │
│   aggregate_and_    │
│   test              │
│   - Metric calcs    │
│   - Significance    │
│   - Slide-ready     │
│     tables          │
└────────┬───────────┘
         │
         ├──────────────────┐
         ▼                  ▼
┌────────────────┐  ┌────────────────┐
│   Tool 3        │  │   Tool 4        │
│   generate_ppt  │  │   generate_     │
│   - python-pptx │  │   narrative     │
│   - Chart gen   │  │   - Claude API  │
│   - Template    │  │   - Cited text  │
│     mapping     │  │   (Phase 2)     │
└────────┬───────┘  └────────┬───────┘
         │                   │
         ▼                   ▼
┌────────────────────────────────────┐
│   report_runs table                 │
│   - Store PPT + Excel paths         │
│   - Mark status COMPLETED           │
│   - Email if async                  │
└─────────────────────────────────────┘
```

**No LLM in the core pipeline.** Tools 1–3 are deterministic Python/SQL. Tool 4 (narrative) uses Claude and is Phase 2.

---

## 12. Phasing

### Phase 1 — Core Pipeline (Build First)
- Project Details table + UI for project setup
- Tool 1: Data pull with QC override JOIN
- QC download/upload workflow
- Tool 2: All metrics from sample reports (SOV, SoA, Reach, Frequency, all breakdowns)
- Tool 2: Significance testing (z-test, t-test, n≥30 threshold)
- Tool 3: PPT generation with standard ZoomRx template
- Excel workbook generation (all aggregated tables)
- Report storage and retrieval
- Multi-wave support

### Phase 2 — Enhancements
- Tool 4: Claude-powered narrative generation
- IA benchmark table and automated refresh
- Client-specific template mapping UI
- Email delivery for async generation
- Ad/email creative image embedding in PPT (brand messaging section)

---

## 13. Open Questions (Resolved)

| # | Question | Resolution |
|---|---|---|
| A1 | DB type? | MySQL |
| A2 | Project Details table? | Must be created (schema in §4.2) |
| A3 | Channel tables? | Separate tables, single `gpt_annotations` (§4.3) |
| A4 | Key columns? | Documented per channel (§4.3) |
| A5 | Brand list source? | Stored in `project_details.brands` at setup time |
| B6-9 | Metrics? | Full list from DTAA skills + sample reports (§5.2) |
| C10 | Interface? | Separate admin portal, form-based (§3) |
| C11 | QC step? | Critical: download → QC → upload corrections (§2, §4.5) |
| D13 | Architecture? | Structured pipeline, not conversational (§3) |
| D14 | LLM? | Claude — for Tool 4 only (§5.4) |
| F19 | Confidence level? | 95% (§5.2.5) |
| F20 | Statistical test? | Z-test (shares), t-test (rates) (§5.2.5) |
| F21 | Pairwise comparison? | Yes — Brand A vs each competitor (§5.2.5) |
| F22 | Min n-size? | 30 (§5.2.5) |
| H26 | QC tables? | Already created by engineering — channel-specific tables: `report_qc_web_contents`, `report_qc_email_senders`, `report_qc_brands`, etc. (§4.5) |
| H27 | Correction history? | No — latest correction overwrites (§4.5) |
| H28 | How Tool 1 uses corrections? | LEFT JOIN channel-specific QC table + COALESCE at query time (§4.5) |
| J34 | Wave representation? | `wave_number` + `start_date` + `end_date` in project config (§4.2) |
| J35 | Multi-wave display? | Side-by-side values per wave (§5.2.4) |
| J36 | Wave with no data? | Blank column + footnote (§5.2.4) |
| K37 | Output delivery? | Portal download + email fallback (§10) |
| K38 | Past runs retrievable? | Yes — stored in `report_runs` table (§4.6, §10) |

---

## 14. Reference Materials

- **Sample Report 1:** Pfizer IBRANCE Digital Tracking Pre-ASCO 2024 (42 slides)
- **Sample Report 2:** Gilead PBC Digital Tracking Q3'25 Final Report (95 slides)
- **Sample Report 3:** Exelixis CABOMETYX Q1'25 Final Report (73 slides)
- **DTAA Skill Reference:** `skills/dtaa/references/schema.md`, `guidelines.md`, `sov_base_template.md`
- **Existing SQL:** Ads channel query with session logic, annotation JOINs, campaign deduplication (provided by Meenakshi)
- **Admin Portal:** PERxCEPT Extension admin portal (screenshot provided)

---

*This PRD is precise enough that a coding agent can begin building Tool 1 immediately without asking a single clarifying question.*
