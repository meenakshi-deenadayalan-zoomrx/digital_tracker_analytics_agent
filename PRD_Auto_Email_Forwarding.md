# PRD: Automated Medical Email Forwarding

**Product**: Digital Tracker (Perxcept panel extension)
**Author**: Meenakshi Deenadayalan
**Date**: 2026-04-20
**Status**: Draft v1

---

## 1. Problem

Today, Perxcept collects promotional medical emails from HCPs via a **manual weekly reminder** flow:

1. Panelist receives a weekly reminder.
2. Panelist opens their mailbox, identifies disease/brand-relevant emails, and forwards them to `info@perxcept.com`.
3. Ingestion pipeline parses the forwarded email.

**Pain points**
- **Low coverage** — HCPs miss or misclassify emails; we only get what they remember to forward.
- **HCP effort** — manual triage costs time each week; drives panel churn.
- **Selection bias** — what gets forwarded is HCP-curated, not exhaustive.
- **Latency** — weekly cadence introduces reporting lag.

## 2. Solution

Add a **one-click auto-forwarding** feature to the Digital Tracker extension. After install and OAuth consent, the extension provisions a server-side mail filter on the HCP's mailbox that auto-forwards every email from Perxcept's curated **Medical Email Senders** list to `info@perxcept.com`.

## 3. Goals & Success Metrics

| Metric | Target (post-launch, per panelist cohort) |
|---|---|
| Avg emails/user/week captured | ≥ 3× vs. manual baseline |
| % of active panelists contributing ≥1 email/month | ≥ 75% (up from current baseline) |
| HCP time spent on email task | ↓ to effectively zero after setup |
| Auto-forward rule retention at 90 days | ≥ 80% of opted-in users |
| Unprompted revocation rate | < 10% within 90 days of enable |

**Tracking**: cohort A/B — new installs on auto-forward vs. holdout on manual reminder — measured over 8 weeks.

## 4. Non-Goals (v1)

- Reading non-promotional / patient-related email (HIPAA risk — see §9).
- Capturing email from mailboxes outside supported providers.
- **Historical backfill** of emails received before the user enabled auto-forwarding. Feature is forward-only by design — avoids restricted OAuth scopes, CASA Tier 2 review, and full-mailbox read access.
- Parsing / enriching forwarded emails (handled by existing ingestion).

## 5. User Flow

1. HCP installs Digital Tracker extension (existing flow).
2. Extension popup shows new onboarding card: **"Turn on automatic email capture"** with value prop and data-use disclosure.
3. User clicks **Enable**.
4. OAuth consent screen (Google or Microsoft) — scopes requested:
   - Gmail: `gmail.settings.basic` (create filter/forward only).
   - Microsoft Graph: `MailboxSettings.ReadWrite` (create message rule only).
5. Backend verifies forwarding target `info@perxcept.com` is confirmed on provider side (one-time setup, see §10).
6. Backend creates a server-side filter: `from:(<sender list>) → forward to info@perxcept.com`.
7. Extension shows success state + **"Forwarding active"** status indicator.


## 6. Senders List

- **Source**: existing `emails` table in Perxcept DB — distinct sender addresses already tagged as medical/promotional.
- **Curation**: a new admin view (out of scope, tracked separately) lets Ops add/remove senders. For v1 ship with top-N senders by historical volume.
- **Sync**: extension backend pulls the senders list nightly and reconciles each user's filter rule if list changed.
- **Rule size limits**: Gmail filters accept long `OR` lists but a single filter is limited (~1500 chars). If list exceeds limit → create multiple filters, or group by domain.

## 7. Deduplication

Every ingested email is hashed on `sha256(lower(sender_email) + "|" + received_date_iso)` where `received_date` is the **date the HCP received the email** (not forwarded date). The hash is the primary dedupe key at ingestion. Existing forwarded-email pipeline must be updated to compute the same hash so manual + auto flows de-duplicate cleanly during the overlap period.

## 8. Consent

- **Initial consent**: OAuth + explicit in-app acknowledgement of (a) forwarding rule creation, (b) what data leaves their mailbox, (c) revocation path. Consent is one-time — no periodic re-confirmation.
- **Revocation**: one-click disable in popup → backend deletes filter rule via API and revokes stored OAuth token.
- **Token loss / expiry**: if refresh fails, extension surfaces a re-auth prompt; rule is left in place (harmless without token) but user is flagged.
- **Persistent status**: popup always shows current forwarding state so user can disable at any time without being prompted.

## 9. Privacy, Compliance, Legal

- **Content scope**: promotional emails from known medical senders only. These are **marketing communications sent to HCPs**, not patient records — they do **not contain PHI** as defined by HIPAA (45 CFR §160.103), because PHI requires individually identifiable health information about a patient.
- **Residual risk**: a sender on the list could, in theory, send an email containing patient-identifiable info (e.g., a case-study newsletter). Mitigations:
  - Sender list is curated to pharma/publisher/CME senders — no provider-to-provider referral senders.
  - Ingestion pipeline scans for PHI markers (SSN, MRN patterns, DOB+name combos) and quarantines matches.
  - BAA is **not** required for v1 because we are not processing PHI on behalf of a covered entity; however, Legal should sign off in writing before GA.
- **GDPR / state privacy (CCPA, etc.)**: HCP is the data subject and gives informed consent. Standard Perxcept privacy policy covers.
- **OAuth app verification**:
  - Google: `gmail.settings.basic` is a **sensitive** scope — requires OAuth consent screen verification (lighter review, a few weeks). Avoids CASA Tier 2 assessment since we never read mailbox content.
  - Microsoft: publisher verification + per-tenant admin consent for enterprise mailboxes. Many hospital tenants will block — document as known limitation.

**Action item**: Legal + Compliance review **before Phase 1 launch**.

## 10. Technical Architecture

### Components

| Component | Responsibility |
|---|---|
| Extension popup UI | Onboarding card, status indicator, revoke button |
| Auth service (new) | OAuth 2.0 flow for Google + Microsoft; token storage (encrypted at rest) |
| Filter-provisioning service (new) | Creates/updates/deletes mail filter rules via provider API |
| Senders-list service (new) | Exposes current senders list; triggers reconciliation on change |
| `info@perxcept.com` inbox | Existing ingestion endpoint; must be verified as forwarding destination on Google side |
| Dedupe layer (update) | Add `sha256(sender|received_date)` hash to email records |

### Provider API details

**Gmail** (Phase 1)
- Scope: `https://www.googleapis.com/auth/gmail.settings.basic`
- Endpoint: `POST users/me/settings/filters` with `criteria.from` + `action.forward`
- Pre-req: `POST users/me/settings/forwardingAddresses` → user clicks verification link emailed to `info@perxcept.com` (one-time, per-user).
- **Verification friction**: the user's Gmail sends a confirmation email to `info@perxcept.com`; our backend must auto-click that verification link (programmatic click from the `info@perxcept.com` mailbox automation). Needed for zero-touch UX.

**Microsoft Graph** (Phase 2)
- Scope: `MailboxSettings.ReadWrite`
- Endpoint: `POST /me/mailFolders/inbox/messageRules` with `conditions.senderContains` + `actions.forwardTo`
- No destination-verification step needed (unlike Gmail).
- Enterprise tenant admins may block external forwarding via transport rule → surface graceful error.

### Token storage
- Refresh tokens encrypted with KMS-managed key.
- Refresh tokens rotated on standard OAuth refresh cycle.
- Revocation on user opt-out deletes token + filter atomically.

## 11. Phased Rollout

### Phase 1 — Gmail forwarding *(MVP, ~6–8 weeks eng)*
- Gmail OAuth + filter provisioning.
- Senders list served from existing `emails` table top-N.
- Extension popup: enable / status / disable.
- Dedupe hash added to ingestion.
- **Exit criteria**: 100 panelists opted in, forwarding rule retention ≥ 80% at 30 days, no PHI incidents.

### Phase 2 — Outlook / Microsoft 365 support *(~4 weeks after Phase 1)*
- Microsoft Graph OAuth + message rule provisioning.
- Handle enterprise tenant consent + transport-rule blocks.
- Unified popup UX (auto-detect provider).

### Phase 3 — Senders-list admin UX + dynamic reconciliation *(~3 weeks)*
- Ops tool to manage senders list.
- Nightly job reconciles each user's filter rule to match current list.
- Diff notifications to Ops on material changes.

### Phase 4 — Additional providers *(exploratory)*
- Yahoo Mail (API limited — may require IMAP fallback).
- Apple iCloud (no public filter API — likely not feasible).
- Document non-supported providers in-app.

## 12. Open Questions

1. Who on Perxcept side owns the `info@perxcept.com` mailbox automation that auto-confirms Gmail forwarding verifications?
2. Do we want the senders list scoped per-HCP (based on their specialty) or global? V1 assumes global.
3. Should revocation also delete previously ingested emails? Default: no — data already consented to at time of receipt.
4. Legal sign-off owner and timeline?

## 13. Dependencies

- Google Cloud project with OAuth consent screen verification (sensitive-scope review).
- Microsoft Entra app registration + publisher verification (Phase 2).
- KMS / secrets infra for token storage.
- Update to ingestion pipeline for hash-based dedupe (must ship alongside Phase 1).
- Legal review sign-off.

## 14. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Google OAuth verification delays Phase 1 | Medium | Medium | Start verification process early; use test-user allowlist for pilot |
| Enterprise tenants block external forwarding | High | Medium | Graceful fallback to manual forward; track blocked-tenant rate |
| No historical data means slow ramp-up of per-user volume | Medium | Low | Accept as tradeoff; communicate via onboarding that capture begins going forward |
| Sender sends PHI-containing email | Low | High | Quarantine scan in ingestion; curated sender list |
| User revokes OAuth silently | Medium | Low | Token-health monitoring; surface re-auth prompt on next popup open |
| Gmail filter char limit exceeded | Medium | Low | Split into multiple filters or group by domain |

---

**Appendix A — Glossary**
- **HCP**: Healthcare Professional (panelist).
- **PHI**: Protected Health Information (HIPAA-regulated).
- **Perxcept**: Panel platform that ingests HCP digital engagement data.
