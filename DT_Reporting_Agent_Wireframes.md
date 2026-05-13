# DT Reporting Agent — Admin Portal Wireframes

**Date:** 2026-04-13  
**For:** Engineering + Design handoff  
**Reference:** DT_Reporting_Agent_PRD_v1.md

---

## Navigation Structure

```
┌──────────────────────────────────────────────────────────────────────┐
│  P  EXTENSION v                                                      │
│ ─────────────────                                                    │
│  Dashboard                                                           │
│  Self Serve Portal                                                   │
│  Web Contents & Email                                                │
│  Ads Gallery                                                         │
│  Posts & Media                                                       │
│  Recording                                                           │
│  Tracked URLs                                                        │
│  Users                                                               │
│  Payment                                                             │
│  Notifications                                                       │
│  Projects                                                            │
│  Specialities                                                        │
│  ─────────────────                                                   │
│  ★ DT Reports        ← NEW NAV ITEM                                 │
│     ├── Projects                                                     │
│     ├── QC Review                                                    │
│     └── Report Runs                                                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Screen 1: DT Reports — Project List

**Route:** `/dt-reports/projects`  
**Purpose:** View all reporting projects, create new ones

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  P  EXTENSION v                                                                      │
│ ┌──────────┐  ┌────────────────────────────────────────────────────────────────────┐ │
│ │           │  │                                                                    │ │
│ │ Dashboard │  │  DT Reporting Projects                          [ + New Project ]  │ │
│ │           │  │                                                                    │ │
│ │ ...       │  │  ┌─────────────────────────────────────────────────────────────┐   │ │
│ │           │  │  │ Search projects...                    Status: [All     v]   │   │ │
│ │           │  │  └─────────────────────────────────────────────────────────────┘   │ │
│ │           │  │                                                                    │ │
│ │           │  │  ┌────────┬──────────────┬───────────┬────────┬────────┬────────┐  │ │
│ │           │  │  │ ID   ▼ │ PROJECT NAME │ CLIENT    │ WAVES  │ STATUS │ ACTIONS│  │ │
│ │★DT Reports│  │  ├────────┼──────────────┼───────────┼────────┼────────┼────────┤  │ │
│ │  Projects │  │  │ 12     │ AZN_Calquence│ AstraZen. │ 3      │●Active │ ⊙ ✎ 📥 │  │ │
│ │  QC Review│  │  │        │ _JulDec      │           │        │        │        │  │ │
│ │  Runs     │  │  ├────────┼──────────────┼───────────┼────────┼────────┼────────┤  │ │
│ │           │  │  │ 11     │ PFE_IBRANCE_ │ Pfizer    │ 1      │●Active │ ⊙ ✎ 📥 │  │ │
│ │           │  │  │        │ PreASCO2024  │           │        │        │        │  │ │
│ │           │  │  ├────────┼──────────────┼───────────┼────────┼────────┼────────┤  │ │
│ │           │  │  │ 10     │ GIL_PBC_Q325 │ Gilead    │ 1      │●Active │ ⊙ ✎ 📥 │  │ │
│ │           │  │  ├────────┼──────────────┼───────────┼────────┼────────┼────────┤  │ │
│ │           │  │  │ 9      │ EXE_CABO_RCC │ Exelixis  │ 4      │○Archvd │ ⊙   📥 │  │ │
│ │           │  │  │        │ _2025        │           │        │        │        │  │ │
│ │           │  │  └────────┴──────────────┴───────────┴────────┴────────┴────────┘  │ │
│ │           │  │                                                                    │ │
│ │           │  │  Showing 1-4 of 4                              < 1 >               │ │
│ └──────────┘  └────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────────┘

ACTIONS KEY:
  ⊙ = View / Generate Report
  ✎ = Edit Project
  📥 = Download Last Run
```

---

## Screen 2: Create / Edit Project

**Route:** `/dt-reports/projects/new` or `/dt-reports/projects/:id/edit`  
**Purpose:** Define all project parameters

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  DT Reporting Projects  >  New Project                                               │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                                 │ │
│  │  PROJECT DETAILS                                                                │ │
│  │  ─────────────────────────────────────────────────────                          │ │
│  │                                                                                 │ │
│  │  Project Name *        [ AZN_Calquence_JulDec__________________________ ]       │ │
│  │                                                                                 │ │
│  │  Client *              [ AstraZeneca                              v ]           │ │
│  │                                                                                 │ │
│  │                                                                                 │ │
│  │  MARKET BASKET                                                                  │ │
│  │  ─────────────────────────────────────────────────────                          │ │
│  │                                                                                 │ │
│  │  Brands *                                                                       │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐           │ │
│  │  │ [Calquence ×] [Brukinsa ×] [Venclexta ×] [Imbruvica ×]          │           │ │
│  │  │ [Jaypirca ×]                                                     │           │ │
│  │  │ Type to add brand...                                             │           │ │
│  │  └───────────────────────────────────────────────────────────────────┘           │ │
│  │                                                                                 │ │
│  │  Diseases *                                                                     │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐           │ │
│  │  │ [CLL ×] [SLL ×]                                                  │           │ │
│  │  │ Type to add disease...                                           │           │ │
│  │  └───────────────────────────────────────────────────────────────────┘           │ │
│  │                                                                                 │ │
│  │  Manufacturers                                                                  │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐           │ │
│  │  │ [AstraZeneca ×] [BeiGene ×] [AbbVie ×] [J&J ×] [Lilly ×]       │           │ │
│  │  │ Type to add manufacturer...                                      │           │ │
│  │  └───────────────────────────────────────────────────────────────────┘           │ │
│  │                                                                                 │ │
│  │                                                                                 │ │
│  │  CHANNELS                                                                       │ │
│  │  ─────────────────────────────────────────────────────                          │ │
│  │                                                                                 │ │
│  │  ☑ Ads (Banner/Display)      ☑ Emails         ☑ Search Results                 │ │
│  │  ☑ Web Content (Browsing)    ☑ Posts (Social)  ☐ AI Responses                   │ │
│  │                                                                                 │ │
│  │                                                                                 │ │
│  │  WAVE DEFINITIONS                                                               │ │
│  │  ─────────────────────────────────────────────────────                          │ │
│  │                                                                                 │ │
│  │  Number of Waves *     [ 3  v ]                                                 │ │
│  │                                                                                 │ │
│  │  ┌───────┬────────────────────────┬────────────────────────┐                    │ │
│  │  │ WAVE  │ START DATE             │ END DATE               │                    │ │
│  │  ├───────┼────────────────────────┼────────────────────────┤                    │ │
│  │  │ W1    │ [ 📅 2024-07-01      ] │ [ 📅 2024-09-30      ] │                    │ │
│  │  ├───────┼────────────────────────┼────────────────────────┤                    │ │
│  │  │ W2    │ [ 📅 2024-10-01      ] │ [ 📅 2024-12-31      ] │                    │ │
│  │  ├───────┼────────────────────────┼────────────────────────┤                    │ │
│  │  │ W3    │ [ 📅 2025-01-01      ] │ [ 📅 2025-03-31      ] │                    │ │
│  │  └───────┴────────────────────────┴────────────────────────┘                    │ │
│  │                                                                                 │ │
│  │                                                                                 │ │
│  │  TARGET LIST                                                                    │ │
│  │  ─────────────────────────────────────────────────────                          │ │
│  │                                                                                 │ │
│  │  Upload NPI List        [ Choose file ]  Browse   (UPLOAD)   Sample CSV ⓘ       │ │
│  │                                                                                 │ │
│  │  Or link to existing project target list:                                       │ │
│  │  Linked Project *      [ AZN_Calquence_JulSep (existing)          v ]           │ │
│  │                                                                                 │ │
│  │  Panel Size:  103 HCPs loaded                                                   │ │
│  │                                                                                 │ │
│  │                                                                                 │ │
│  │            [ Cancel ]                              [ Save Project ]              │ │
│  │                                                                                 │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 3: Project Dashboard / Report Generation

**Route:** `/dt-reports/projects/:id`  
**Purpose:** Central hub — view project, trigger data pull, QC, and report generation

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  DT Reporting Projects  >  AZN_Calquence_JulDec                          [ ✎ Edit ] │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────┐       │
│  │  PROJECT SUMMARY                                                         │       │
│  │                                                                           │       │
│  │  Client: AstraZeneca          Channels: Ads, Email, Search, Web, Posts   │       │
│  │  Brands: Calquence, Brukinsa, Venclexta, Imbruvica, Jaypirca            │       │
│  │  Diseases: CLL, SLL           Panel: 103 HCPs                            │       │
│  │  Waves: 3 (Jul-Sep '24, Oct-Dec '24, Jan-Mar '25)                       │       │
│  │  Data Freshness: 2026-04-12 23:45 UTC                                    │       │
│  │  ⚠ Data is 1 day old                                                     │       │
│  └───────────────────────────────────────────────────────────────────────────┘       │
│                                                                                      │
│                                                                                      │
│  ┌─── STEP 1: DATA PULL & QC ───────────────────────────────────────────────────┐   │
│  │                                                                               │   │
│  │  Select waves for this run:                                                   │   │
│  │  ☑ Wave 1: Jul 1 – Sep 30, 2024                                              │   │
│  │  ☑ Wave 2: Oct 1 – Dec 31, 2024                                              │   │
│  │  ☑ Wave 3: Jan 1 – Mar 31, 2025                                              │   │
│  │                                                                               │   │
│  │  Select channels:                                                             │   │
│  │  ☑ Ads   ☑ Emails   ☑ Search   ☑ Web Content   ☑ Posts                       │   │
│  │                                                                               │   │
│  │  [ 📥 Pull Data & Download for QC ]                                           │   │
│  │                                                                               │   │
│  │  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─       │   │
│  │                                                                               │   │
│  │  QC Downloads:                                                                │   │
│  │  ┌─────────────────┬──────────┬──────────────┬───────────┐                    │   │
│  │  │ CHANNEL          │ RECORDS  │ LAST PULLED   │ ACTION    │                    │   │
│  │  ├─────────────────┼──────────┼──────────────┼───────────┤                    │   │
│  │  │ Ads              │ 1,245    │ Apr 13 10:30  │ 📥 CSV    │                    │   │
│  │  │ Emails           │ 340      │ Apr 13 10:30  │ 📥 CSV    │                    │   │
│  │  │ Search Results   │ 2,100    │ Apr 13 10:30  │ 📥 CSV    │                    │   │
│  │  │ Web Content      │ 8,612    │ Apr 13 10:30  │ 📥 CSV    │                    │   │
│  │  │ Posts            │ 420      │ Apr 13 10:30  │ 📥 CSV    │                    │   │
│  │  └─────────────────┴──────────┴──────────────┴───────────┘                    │   │
│  │                                                                               │   │
│  └───────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│                                                                                      │
│  ┌─── STEP 2: UPLOAD QC CORRECTIONS ────────────────────────────────────────────┐   │
│  │                                                                               │   │
│  │  Upload corrected brand/disease mappings:                                     │   │
│  │                                                                               │   │
│  │  [ Choose file ]  Browse   (UPLOAD CORRECTIONS)   Sample CSV ⓘ               │   │
│  │                                                                               │   │
│  │  QC Status:                                                                   │   │
│  │  ┌─────────────────┬──────────────┬───────────┬────────────────────────┐      │   │
│  │  │ CHANNEL          │ CORRECTIONS  │ UPLOADED   │ UPLOADED BY            │      │   │
│  │  ├─────────────────┼──────────────┼───────────┼────────────────────────┤      │   │
│  │  │ Ads              │ 42           │ Apr 13 14:│ meenakshi@zoomrx.com   │      │   │
│  │  │ Emails           │ 8            │ Apr 13 14:│ meenakshi@zoomrx.com   │      │   │
│  │  │ Search Results   │ 0            │ —         │ —                      │      │   │
│  │  │ Web Content      │ 15           │ Apr 13 15:│ meenakshi@zoomrx.com   │      │   │
│  │  │ Posts            │ 3            │ Apr 13 15:│ meenakshi@zoomrx.com   │      │   │
│  │  └─────────────────┴──────────────┴───────────┴────────────────────────┘      │   │
│  │                                                                               │   │
│  │  Total corrections applied: 68 across 5 channels                              │   │
│  │                                                                               │   │
│  └───────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│                                                                                      │
│  ┌─── STEP 3: GENERATE REPORT ──────────────────────────────────────────────────┐   │
│  │                                                                               │   │
│  │  Report Configuration:                                                        │   │
│  │                                                                               │   │
│  │  Template:    [ Standard ZoomRx DT Template          v ]                      │   │
│  │  Output:      ☑ PowerPoint (.pptx)    ☑ Excel (.xlsx)                         │   │
│  │  Narrative:   ☐ Generate AI narrative (Phase 2)                               │   │
│  │                                                                               │   │
│  │  Delivery:    ◉ Download in browser                                           │   │
│  │               ○ Email to: [ meenakshi@zoomrx.com_____________ ]               │   │
│  │                                                                               │   │
│  │                                                                               │   │
│  │           [ Generate Report ]                                                 │   │
│  │                                                                               │   │
│  └───────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│                                                                                      │
│  ┌─── PAST RUNS ────────────────────────────────────────────────────────────────┐   │
│  │                                                                               │   │
│  │  ┌──────┬────────────────────┬──────────────┬──────────┬─────────┬──────────┐ │   │
│  │  │ RUN  │ WAVES              │ GENERATED     │ BY       │ STATUS  │ DOWNLOAD │ │   │
│  │  ├──────┼────────────────────┼──────────────┼──────────┼─────────┼──────────┤ │   │
│  │  │ #3   │ W1, W2, W3         │ Apr 13 16:20  │ Meenakshi│ ●Done   │ 📥 📊    │ │   │
│  │  │ #2   │ W1, W2             │ Apr 10 11:00  │ Meenakshi│ ●Done   │ 📥 📊    │ │   │
│  │  │ #1   │ W1                 │ Mar 28 09:45  │ Raj      │ ●Done   │ 📥 📊    │ │   │
│  │  └──────┴────────────────────┴──────────────┴──────────┴─────────┴──────────┘ │   │
│  │                                                                               │   │
│  │  📥 = Download PPT    📊 = Download Excel                                     │   │
│  │                                                                               │   │
│  └───────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 4: QC Download — CSV Preview

**Route:** Modal / drawer from Screen 3  
**Purpose:** Preview entity-level raw data before downloading for QC

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                      │
│  QC Data Preview — Ads Channel                          Wave: All    [ 📥 Download ] │
│                                                                                      │
│  Showing 1,245 records across 3 waves                                                │
│  ⚠ Brand/disease values are from GPT annotations — ~90% accurate. Review and        │
│    correct any errors, then upload the corrected CSV.                                 │
│                                                                                      │
│  ┌───────┬─────────┬──────────┬────────────┬──────────────┬──────────┬────────────┐  │
│  │ AD_ID │ USER_ID │ WAVE     │ AD_DATE    │ BRAND        │ DISEASE  │ AD_TYPE    │  │
│  │       │         │          │            │ (review)     │ (review) │            │  │
│  ├───────┼─────────┼──────────┼────────────┼──────────────┼──────────┼────────────┤  │
│  │ 44201 │ 32745   │ W1       │ 2024-07-15 │ Calquence    │ CLL      │ STATIC     │  │
│  ├───────┼─────────┼──────────┼────────────┼──────────────┼──────────┼────────────┤  │
│  │ 44202 │ 32745   │ W1       │ 2024-07-15 │ Brukinsa     │ CLL      │ DYNAMIC    │  │
│  ├───────┼─────────┼──────────┼────────────┼──────────────┼──────────┼────────────┤  │
│  │ 44203 │ 45568   │ W1       │ 2024-07-16 │ ⚠ Imbruvica  │ ⚠ NHL    │ STATIC     │  │
│  │       │         │          │            │ (low conf.)  │(low conf)│            │  │
│  ├───────┼─────────┼──────────┼────────────┼──────────────┼──────────┼────────────┤  │
│  │ 44204 │ 45568   │ W1       │ 2024-07-16 │ Venclexta    │ CLL      │ CANVAS     │  │
│  ├───────┼─────────┼──────────┼────────────┼──────────────┼──────────┼────────────┤  │
│  │ ...   │ ...     │ ...      │ ...        │ ...          │ ...      │ ...        │  │
│  └───────┴─────────┴──────────┴────────────┴──────────────┴──────────┴────────────┘  │
│                                                                                      │
│  Columns in downloaded CSV:                                                          │
│  entity_id, entity_type, user_id, wave, date, brand, disease, manufacturer,          │
│  url, content_preview, annotation_confidence, session_id                              │
│                                                                                      │
│  ⓘ Edit brand/disease columns in the CSV. Upload only rows you changed.              │
│    Unchanged rows will keep their original annotation values.                         │
│                                                                                      │
│                                    [ Close ]              [ 📥 Download Full CSV ]    │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 5: QC Upload — Corrections Review

**Route:** Modal / drawer from Screen 3 after upload  
**Purpose:** Confirm corrections before saving

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                      │
│  Upload QC Corrections — Ads Channel                                                 │
│                                                                                      │
│  File: ads_qc_corrections_apr13.csv                                                  │
│  Rows with changes detected: 42                                                      │
│                                                                                      │
│  ┌───────┬─────────────┬────────────┬─────────────┬────────────┬──────────────────┐  │
│  │ AD_ID │ FIELD       │ ORIGINAL   │ CORRECTED   │ CHANGED BY │ STATUS           │  │
│  ├───────┼─────────────┼────────────┼─────────────┼────────────┼──────────────────┤  │
│  │ 44203 │ brand       │ Imbruvica  │ Calquence   │ Meenakshi  │ ● New            │  │
│  │ 44203 │ disease     │ NHL        │ CLL         │ Meenakshi  │ ● New            │  │
│  │ 44289 │ brand       │ Venclexta  │ Brukinsa    │ Meenakshi  │ ● New            │  │
│  │ 44301 │ brand       │ Calquence  │ [REMOVE]    │ Meenakshi  │ ● New            │  │
│  │ 44315 │ disease     │ CLL        │ MCL         │ Meenakshi  │ ● Updated        │  │
│  │       │             │            │             │            │ (prev: SLL)      │  │
│  │ ...   │ ...         │ ...        │ ...         │ ...        │ ...              │  │
│  └───────┴─────────────┴────────────┴─────────────┴────────────┴──────────────────┘  │
│                                                                                      │
│  Summary:                                                                            │
│  ┌────────────────────────────────────────────────┐                                  │
│  │  New corrections:          38                   │                                  │
│  │  Updated corrections:      4                    │                                  │
│  │  Brand changes:            28                   │                                  │
│  │  Disease changes:          14                   │                                  │
│  │  Removals ([REMOVE]):      2                    │                                  │
│  └────────────────────────────────────────────────┘                                  │
│                                                                                      │
│  ⚠ 2 records marked [REMOVE] will be excluded from all aggregations.                 │
│                                                                                      │
│             [ Cancel ]                          [ Apply 42 Corrections ]              │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 6: Report Generation — Progress & Confirmation

**Route:** `/dt-reports/projects/:id/generate` (or modal overlay)  
**Purpose:** Show config echo for confirmation, then generation progress

### 6a: Confirmation Step

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                      │
│  Confirm Report Generation                                                           │
│                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                                │  │
│  │  PROJECT         AZN_Calquence_JulDec                                          │  │
│  │  CLIENT          AstraZeneca                                                   │  │
│  │  BRANDS          Calquence, Brukinsa, Venclexta, Imbruvica, Jaypirca           │  │
│  │  DISEASES        CLL, SLL                                                      │  │
│  │  PANEL SIZE      103 HCPs                                                      │  │
│  │                                                                                │  │
│  │  WAVES           W1: Jul–Sep 2024                                              │  │
│  │                  W2: Oct–Dec 2024                                               │  │
│  │                  W3: Jan–Mar 2025                                               │  │
│  │                                                                                │  │
│  │  CHANNELS        Ads, Emails, Search Results, Web Content, Posts               │  │
│  │                                                                                │  │
│  │  QC CORRECTIONS  68 corrections applied (42 Ads, 8 Emails, 15 Web, 3 Posts)    │  │
│  │                                                                                │  │
│  │  DATA FRESHNESS  Apr 12, 2026 23:45 UTC (1 day ago)                            │  │
│  │                                                                                │  │
│  │  TEMPLATE        Standard ZoomRx DT Template                                   │  │
│  │  OUTPUT          PPT + Excel                                                   │  │
│  │                                                                                │  │
│  └────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  Please review the configuration above. The report will be generated with             │
│  these exact parameters.                                                             │
│                                                                                      │
│             [ Back to Edit ]                        [ Confirm & Generate ]            │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### 6b: Generation Progress

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                      │
│  Generating Report — AZN_Calquence_JulDec                                            │
│                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                                │  │
│  │  ████████████████████████████░░░░░░░░░░░░  65%                                 │  │
│  │                                                                                │  │
│  │  ✅ Step 1: Data pull complete               (1,245 ads, 340 emails, ...)      │  │
│  │  ✅ Step 2: QC corrections applied            (68 overrides)                   │  │
│  │  ✅ Step 3: Metrics aggregated                (SOV, Reach, Frequency, ...)     │  │
│  │  ✅ Step 4: Significance testing complete     (95% CI, n≥30 enforced)          │  │
│  │  🔄 Step 5: Generating PowerPoint...          (Slide 28 of 45)                │  │
│  │  ⬜ Step 6: Generating Excel workbook                                          │  │
│  │  ⬜ Step 7: Saving to report_runs                                              │  │
│  │                                                                                │  │
│  │  Estimated time remaining: ~45 seconds                                         │  │
│  │                                                                                │  │
│  └────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ⓘ If this takes longer than 1 minute, you'll receive the files via email.           │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### 6c: Generation Complete

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                      │
│  ✅ Report Generated Successfully                                                    │
│                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                                │  │
│  │  Project:    AZN_Calquence_JulDec                                              │  │
│  │  Run #3:     Apr 13, 2026 16:20                                                │  │
│  │  Waves:      W1, W2, W3                                                        │  │
│  │                                                                                │  │
│  │  ┌────────────────────────────────────────────────────────────────────┐         │  │
│  │  │                                                                    │         │  │
│  │  │  📄  AZN_Calquence_JulDec_Report_W1W2W3.pptx        [ 📥 Download ]│        │  │
│  │  │      45 slides  •  12.3 MB                                        │         │  │
│  │  │                                                                    │         │  │
│  │  │  📊  AZN_Calquence_JulDec_Tables_W1W2W3.xlsx        [ 📥 Download ]│        │  │
│  │  │      8 sheets  •  2.1 MB                                          │         │  │
│  │  │                                                                    │         │  │
│  │  └────────────────────────────────────────────────────────────────────┘         │  │
│  │                                                                                │  │
│  │  Report Metadata:                                                              │  │
│  │  • 103 HCPs in panel                                                           │  │
│  │  • 12,717 total records processed                                              │  │
│  │  • 68 QC corrections applied                                                   │  │
│  │  • 14 significance tests flagged (n≥30)                                        │  │
│  │  • 3 tests suppressed (low sample size)                                        │  │
│  │  • Data freshness: Apr 12, 2026                                                │  │
│  │                                                                                │  │
│  └────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│        [ ← Back to Project ]              [ Generate Another Run ]                   │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 7: Report Runs History

**Route:** `/dt-reports/runs`  
**Purpose:** Browse all past report runs across projects

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  DT Reports  >  Report Runs                                                          │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │ Project: [All Projects      v]   Status: [All    v]   Date: [Last 30 days v]│    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  ┌──────┬──────────────────┬──────────┬──────────────┬──────────┬─────────┬────────┐ │
│  │ RUN  │ PROJECT          │ WAVES    │ GENERATED     │ BY       │ STATUS  │ FILES  │ │
│  ├──────┼──────────────────┼──────────┼──────────────┼──────────┼─────────┼────────┤ │
│  │ #12  │ AZN_Calquence    │ W1,W2,W3 │ Apr 13 16:20  │ Meenakshi│ ●Done   │ 📥 📊  │ │
│  │ #11  │ GIL_PBC_Q325     │ W1       │ Apr 12 14:00  │ Raj      │ ●Done   │ 📥 📊  │ │
│  │ #10  │ AZN_Calquence    │ W1,W2    │ Apr 10 11:00  │ Meenakshi│ ●Done   │ 📥 📊  │ │
│  │ #9   │ PFE_IBRANCE      │ W1       │ Apr 08 09:30  │ Sarah    │ ●Done   │ 📥 📊  │ │
│  │ #8   │ EXE_CABO_RCC     │ W1–W4    │ Apr 05 16:45  │ Raj      │ ●Emailed│ 📥 📊  │ │
│  │ #7   │ GIL_PBC_Q325     │ W1       │ Apr 01 10:15  │ Raj      │ ●Done   │ 📥 📊  │ │
│  └──────┴──────────────────┴──────────┴──────────────┴──────────┴─────────┴────────┘ │
│                                                                                      │
│  Showing 1-6 of 12                                         < 1  2 >                  │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## QC CSV Format Specification

### Download Format (one per channel)

```
entity_id | entity_type | user_id | wave | date       | brand      | disease | manufacturer  | url/content_preview        | annotation_confidence
44201     | AD          | 32745   | W1   | 2024-07-15 | Calquence  | CLL     | AstraZeneca   | https://onclive.com/...    | 0.95
44202     | AD          | 32745   | W1   | 2024-07-15 | Brukinsa   | CLL     | BeiGene       | https://medscape.com/...   | 0.92
44203     | AD          | 45568   | W1   | 2024-07-16 | Imbruvica  | NHL     | J&J           | https://nejm.org/...       | 0.67
```

### Upload Format (corrections only — rows that changed)

```
entity_id | entity_type | brand      | disease
44203     | AD          | Calquence  | CLL
44289     | AD          | Brukinsa   | CLL
44301     | AD          | [REMOVE]   | [REMOVE]
```

- Only include rows where brand or disease was changed
- `[REMOVE]` = exclude this entity from all aggregations
- System validates: entity_id must exist in the pulled data for this project

---

## Component Library Notes (for Design)

| Component | Behavior |
|---|---|
| Tag Input (brands, diseases, manufacturers) | Multi-select with typeahead, chips with ×, free-text entry allowed |
| Date Picker (wave definitions) | Calendar picker, validates end > start, no overlap between waves |
| Channel Checkboxes | At least 1 required. Toggle all / none |
| File Upload (NPI list, QC CSV) | Drag-and-drop zone, accepts .csv only, shows row count after parse |
| Progress Bar (report gen) | Real-time updates via WebSocket, step-by-step with checkmarks |
| Download Buttons | Distinct icons for PPT (📄) vs Excel (📊), hover shows file size |
| Status Badges | ●Active (green), ○Archived (gray), ●Done (green), ●Emailed (blue), ●Failed (red), 🔄Generating (yellow spin) |
| Data Freshness Warning | Yellow banner if >7 days, red if >14 days |
| Confirmation Modal | Echoes all config parameters, requires explicit click to proceed |

---

## Responsive Behavior

- **Primary target:** Desktop (1280px+) — this is an internal tool used by consultants on laptops
- **Minimum supported:** 1024px width
- **No mobile support required** — portal is desktop-only

---

*End of wireframes. Ready for design handoff.*
