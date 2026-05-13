# Digital Tracker — Tech Team Onboarding
### Prepared for: Nakul | April 2026

---

# SLIDE 1: Welcome & Agenda

**Welcome to the Digital Tracker Team!**

Today's agenda:
1. What is Digital Tracker? (Product & Business Context)
2. Reports We Deliver to Clients
3. Data Sources & Architecture
4. Team Structure & Workflows
5. Product ↔ Tech Interaction Model
6. Current & Upcoming Projects
7. Q&A

---

# SLIDE 2: What is Digital Tracker?

**One-stop-shop for omnichannel intelligence in pharma**

Digital Tracker provides visibility into every digital campaign in a therapeutic market — from the customer's (HCP's) point of view.

**Two data collection engines:**
- **PERxCEPT Extension** (panelist-based): Browser extension installed by HCP panelists — captures real browsing, ads, emails, search results
- **PERxCEPT Crawler** (web scraping): Google-like crawling of the life sciences web — captures campaigns, paid search ads, social media posts

**Think of it as:** "Google for Pharma" + "Nielsen Box for HCPs"

---

# SLIDE 3: Who Uses It & Why?

**Clients:** Pharma brand teams (e.g., Exelixis/Cabometyx, Pfizer/Ibrance, Gilead/Livdelzi)

**They want to know:**
- What are HCPs seeing online about my brand vs. competitors?
- Where do target HCPs spend time browsing?
- What's my digital Share of Voice across channels?
- Are my paid search ads outranking competitors?
- What competitor emails/ads are reaching my target HCPs?
- Is my digital spend effective?

**Deliverable:** Quarterly PowerPoint reports with data-backed insights & recommendations

---

# SLIDE 4: The 5 Channels We Track

| Channel | What We Capture | Data Source |
|---|---|---|
| **Brand Engagement (Web Browsing)** | URLs, page content, time spent on healthcare websites | Extension only |
| **Banner/Display Ads** | Every display & programmatic ad seen during browsing | Extension + Crawler |
| **Paid Search** | All Google results labeled "Sponsored" for TA keywords | Extension + Crawler |
| **Email** | Forwarded healthcare emails (manufacturer, rep, 3rd party) | Extension only |
| **Social Media / Posts** | Ads on Meta, YouTube, Sermo, LinkedIn, Twitter/X | Extension + Crawler |

---

# SLIDE 5: Anatomy of a Client Report

**Standard Report Structure:**

| Section | Content |
|---|---|
| **Introduction** | What is DT, methodology, panel profile |
| **Executive Summary** | Digital footprint scorecard, key findings, recommendations |
| **Channel Deep-Dives** | Browsing → Web Ads → Paid Search → Social Media → Email |
| **Brand Messaging** | Key messaging themes with ad creative screenshots |
| **Appendix** | Search keywords, campaign details, methodology notes |

> **See attached sample reports** (Exelixis Cabometyx Q1'25, Pfizer Ibrance Pre-ASCO 2024, Gilead PBC Q3'25) for full examples

---

# SLIDE 6: Sample Slide Types (What Reports Look Like)

**Browsing Activity:** Bubble charts — Reach vs. Frequency, with bubble size = Share of Time
- Top websites by indication (e.g., nccn.org, uptodate.com, medscape.com)

**Web Ads SOV:** Stacked bar charts — Brand share of ad exposure per HCP over quarters

**Paid Search:** Horizontal bar charts — Brand share by rank position (1st, 2nd, 3rd, 4+)

**Email SOV:** Donut charts — Brand share of forwarded emails, split by sender type (manufacturer / rep / 3rd party)

**Social Media:** Platform-level exposure tables (Sermo, LinkedIn, Facebook, YouTube, Twitter/X)

**Brand Messaging:** Ad creative screenshots with messaging theme classification

---

# SLIDE 7: Key Metrics & Methodology

| Metric | Definition |
|---|---|
| **Reach** | % of HCPs with brand encounters (# unique HCPs with exposure / total panel) |
| **Frequency** | # of exposures per HCP who was exposed |
| **Share of Voice (SOV)** | Average of each HCP's brand share — NOT weighted aggregate (prevents one heavy user from skewing) |
| **Share of Attention** | For web browsing: weighted by time spent AND brand mention count on the page |
| **Share of Exposure** | For paid search/ads: % of brand-specific results/ads seen by HCPs |

**SOV Methodology (Panelist):**
- Per-HCP brand share is calculated first
- Then averaged across all HCPs
- This prevents a single power-user from dominating the metric
- (See Exelixis report slide 8 for visual explanation)

---

# SLIDE 8: Data Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    DATA COLLECTION                       │
│                                                         │
│  PERxCEPT Extension          PERxCEPT Crawler           │
│  (Chrome/iOS/macOS)          (Server-side scraping)      │
│  ─ Web browsing              ─ Paid search results       │
│  ─ Banner ads seen           ─ Social media posts        │
│  ─ Paid search results       ─ FB/Insta campaigns        │
│  ─ Social media (browser)    ─ Twitter/X posts           │
│  ─ Email forwarding          ─ Web ad campaigns          │
│  ─ Time on page              ─ Estimated impressions     │
├─────────────────────────────────────────────────────────┤
│                    PROCESSING                            │
│                                                         │
│  Ferma.ai / GPT Annotations                             │
│  ─ Brand tagging                                         │
│  ─ Disease/indication tagging                            │
│  ─ Content classification                                │
│  ─ HCP vs Patient targeting                              │
├─────────────────────────────────────────────────────────┤
│                    STORAGE                                │
│                                                         │
│  MySQL Database (PERxCEPT DB)                            │
│  Key tables:                                             │
│  ─ ads, emails, search_results, web_contents, posts      │
│  ─ gpt_annotations (central brand/disease tagging hub)   │
│  ─ gpt_annotations_diseases_brands (junction table)      │
│  ─ report_qc_* tables (consultant corrections)           │
│  ─ project_details, project_target_list                  │
├─────────────────────────────────────────────────────────┤
│                    REPORTING                              │
│                                                         │
│  Manual today → Automating (Report Automation Pipeline)  │
│  Excel workbooks → PowerPoint decks → AI narratives      │
└─────────────────────────────────────────────────────────┘
```

---

# SLIDE 9: Database — Key Tables

| Table | Purpose |
|---|---|
| `web_contents` | Every healthcare webpage visit (URL, HTML content, time spent) |
| `ads` | Every banner/display ad captured during browsing |
| `emails` | Forwarded healthcare emails |
| `search_results` | Paid search results (Google Sponsored) |
| `posts` | Social media posts (via `web_content_posts` → `web_contents`) |
| `ai_responses` | AI overview/reference captures (newer channel) |
| `gpt_annotations` | Central hub: brand/disease/manufacturer tagging for ALL content |
| `gpt_annotations_diseases_brands` | Junction table with `weight` for multi-brand pages |
| `report_qc_*` | 8 channel-specific QC correction tables |
| `project_details` | Project config (brands, diseases, channels, waves, target NPIs) |

---

# SLIDE 10: Team Structure

```
                    Digital Tracker Team
                           │
            ┌──────────────┴──────────────┐
            │                             │
      Product Team                   Tech Team
            │                             │
     Rob (Product Manager)       Ram Shankar (Sr. Dev)
     Meenakshi (Product Dev      Kam Akshi (Sr. Dev)
       & Execution Manager)      Nakul (New - DevOps) ← YOU
            │
     Aniket (Assoc. Consultant)
     Srirangini (Assoc. Consultant)
```

**Consulting Teams** (separate, client-facing) own the client relationship and final report.
They come to us for data, support, and product expertise.

---

# SLIDE 11: Who Does What

| Role | Responsibilities |
|---|---|
| **Product Team** | Enables consulting teams with data; acts as product SMEs; defines requirements for new features; QC methodology; manages report automation pipeline |
| **Tech Team** | Builds & maintains PERxCEPT extension (Chrome/iOS/macOS) and crawler; ensures data capture quality; builds data pipeline features; DevOps & infrastructure |
| **Consulting Teams** | Own client relationships; build final PPT reports; do QC on data; present findings to clients |

---

# SLIDE 12: Product ↔ Tech Request Lifecycle

```
1. REQUIREMENT SURFACES
   ─ Client asks for new feature (e.g., capture AI overviews)
   ─ Or product team identifies gap (e.g., selector broke on medscape.com)
   ─ Or internal improvement (e.g., automate Excel generation)
                    │
                    ▼
2. PRODUCT TEAM SCOPES
   ─ Meenakshi / Rob define what's needed
   ─ Write spec or create Phabricator ticket
   ─ Prioritize against roadmap
                    │
                    ▼
3. TECH TEAM PICKS UP
   ─ Ram Shankar / Kam Akshi estimate & plan
   ─ Nakul handles DevOps / infrastructure tasks
   ─ Work tracked in Phabricator (Maniphest tickets)
                    │
                    ▼
4. DEVELOPMENT & TESTING
   ─ Code in GitHub repos (extension, crawler, backend)
   ─ Testing against live sites (Playwright for selectors)
   ─ Database migrations if schema changes
                    │
                    ▼
5. DEPLOYMENT & VALIDATION
   ─ Deploy to production
   ─ Product team validates data is flowing correctly
   ─ Volume monitoring for regressions
                    │
                    ▼
6. ONGOING MONITORING
   ─ DTSA agent helps diagnose tracking issues
   ─ Product team monitors volumes, escalates drops
   ─ Tech team fixes selector breaks, code regressions
```

---

# SLIDE 13: Tools & Systems

| System | Purpose | Who Uses It |
|---|---|---|
| **Phabricator (Maniphest)** | Ticket tracking for bugs & features | Product ↔ Tech |
| **GitHub** | Source code for extension, crawler, backend | Tech |
| **MySQL (PERxCEPT DB)** | Production database — all channel data | Tech + Product (read) |
| **PERxCEPT Admin Portal** | Project setup, QC workflows, report generation | Product + Consulting |
| **DTSA Agent** | AI agent for diagnosing tracking issues | Product |
| **DTAA Agent** | AI agent for analytics queries (SOV, Reach, etc.) | Product |
| **Playwright** | Testing CSS/XPath selectors against live sites | Product (via DTSA) |

---

# SLIDE 14: Current Projects — Report Automation Pipeline

**The Big One: "Synapse for Digital Tracker"**

End-to-end automation of the quarterly report generation process.

| Phase | Status | What It Does |
|---|---|---|
| **Phase 1** | LAUNCHED | Automated data pull → Excel workbooks. Consultant selects project, system queries DB for all channels/waves, produces formatted Excel. |
| **Phase 2** | NEXT | Excel → PowerPoint. Auto-populate chart slides from Excel data. Template-based deck generation. |
| **Phase 3** | FUTURE | AI-generated insights. Claude generates talking headers, key findings, and recommendations from the data. |

**Current workflow (manual):** Consultant writes SQL → copies to Excel → builds charts in PPT → writes insights
**Target workflow (automated):** Consultant selects project → clicks "Generate" → gets PPT with insights

---

# SLIDE 15: Current Projects — Other Initiatives

| Initiative | Description | Status |
|---|---|---|
| **AI Overview Capture** | Track AI-generated answers (e.g., Google AI Overviews) that mention brands | Upcoming |
| **AI Website Tracking** | Capture content from AI-native platforms like OpenEvidence.com | Upcoming |
| **DTSA Agent** | AI agent that diagnoses tracking issues (volume drops, selector breaks) using MCP tools | Active |
| **DTAA Agent** | AI agent for on-demand analytics queries against the DB | Active |

---

# SLIDE 16: Where DevOps Fits In

**As the DevOps lead joining this team, here are key areas you'll touch:**

1. **Extension Deployment Pipeline** — Chrome, iOS, macOS extensions need CI/CD
2. **Crawler Infrastructure** — Server-side scraping at scale (900+ healthcare sites/week)
3. **Database Operations** — MySQL performance, migrations, read replicas
4. **Report Automation Backend** — The admin portal + data pipeline services
5. **Monitoring & Alerting** — Data volume monitoring to catch capture failures early
6. **AI Agent Infrastructure** — MCP server hosting, Claude API integration

---

# SLIDE 17: Key Concepts to Know

| Term | Meaning |
|---|---|
| **Panelist** | An HCP who has installed the PERxCEPT extension and is being tracked |
| **Scraper** | Data from the PERxCEPT crawler (machine-based, not actual HCP activity) |
| **Market Basket** | The set of brands being tracked for a given client project |
| **Wave** | A time period for reporting (usually quarterly: Q1, Q2, Q3, Q4) |
| **Endemic Website** | Healthcare-related website (e.g., medscape.com, nccn.org) |
| **Non-Endemic Website** | Non-healthcare site where programmatic ads appear |
| **SOV** | Share of Voice — brand's share of all digital exposures |
| **Share of Attention** | Web-specific: weighted by time spent + brand mention frequency |
| **QC** | Quality Control — consultant corrections to AI-generated brand/disease tags |
| **Ferma.ai** | Our AI tagging system that classifies content by brand, disease, indication |
| **NPI** | National Provider Identifier — unique ID for each HCP |

---

# SLIDE 18: Useful Resources

- **Sample Reports** (attached separately):
  - Exelixis Cabometyx RCC+NET — Q1 2025 (73 slides, full quarterly report)
  - Pfizer Ibrance mBC — Pre-ASCO 2024 (42 slides, example slide types)
  - Gilead PBC — Q3 2025 (95 slides, DT + Pulse Survey combined)

- **DT Reporting Agent PRD** — `DT_Reporting_Agent_PRD_v1.md` (full spec for report automation)

- **DTSA/DTAA Skills** — AI agent skills in `skills/` directory

- **Database Schema** — Ask Meenakshi for read-replica access

---

# SLIDE 19: Q&A

**Questions?**

Key contacts:
- **Meenakshi** — Product development, execution, DTSA/DTAA agents, report automation
- **Rob** — Product strategy, roadmap, stakeholder management
- **Ram Shankar** — Extension/crawler codebase, senior tech questions
- **Kam Akshi** — Extension/crawler development

---

# APPENDIX: Report Type Variations

Different clients get different report flavors:

| Report Type | Example | Key Difference |
|---|---|---|
| **Standard Quarterly** | Exelixis Cabometyx | Full 5-channel analysis, QoQ trends, brand messaging |
| **Conference Tracking** | Pfizer Ibrance Pre-ASCO | Baseline vs. post-conference engagement comparison |
| **DT + Pulse Survey** | Gilead PBC | Digital tracking + follow-up HCP survey for ad recall/impact measurement |
| **Ad Hoc / Custom** | Varies | Client-specific KBQs (Key Business Questions) drive the analysis |
