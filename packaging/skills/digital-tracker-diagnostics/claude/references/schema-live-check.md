# Verified live diagnostic schema compatibility

Read this before choosing any diagnostic database or selector-audit SQL pattern.

Evidence: native authenticated Perxcept metadata checks on 2026-10-09 returned 118 column rows (LIMIT 200) and nine table rows (LIMIT 50), so these requested metadata sets did not reach their result limits. The same connection accepted a read-only WITH/SELECT CTE probe. This evidence contains no business records.

| Historical pattern | Live extension metadata | Decision |
|---|---|---|
| Web/email capture volume via web_contents.visited_timestamp | visited_timestamp and email join keys exist | Retain the original capture-period query; not the analytics received_date definition. |
| Platform breakdown via clients.device_type/device_platform | Both columns exist | Retain the original grouped comparison. |
| Active client users via last_request/is_data_collectable | Both columns exist | Retain original filters and DISTINCT user counting. |
| Search volume via search_queries.created_at | created_at absent; created and timestamp exist | Do not execute that historical pattern. The owner must identify capture/ingestion versus event timestamp before it is revised. |
| Social posts via posts.created_at | created_at absent; created and date exist; web_content_posts and web_contents.created also exist | Do not substitute a date or a join automatically. The owner must confirm which capture event/count definition the diagnostic means. The analytics skill keeps its established web_content_posts → web_contents.created metric convention. |
| AI responses via ai_responses.created_at | created_at absent; created and modified exist | Do not execute that historical pattern until the intended response event time is confirmed. |
| Background status via background_requests | Table not visible in perxcept_extension | Report this check unavailable on the supplied extension source. Do not switch to crawler/archive data or infer that no background failures exist. |
| Selector audit query uses audit_logs.event and created_at | Both absent; audit_event_id, display_text, data and created exist | Do not execute the old example or assume event ID meanings. Obtain the selector audit event mapping/source from the tracker owner. |

The examples in database.md/selectors.md are preserved historical templates. This verified compatibility table controls which may be materialized and executed; a blocked example is not a ready query. A currently unsupported branch is reported explicitly alongside the checks that succeeded. Keep the original current/-7d/-28d windows, classification thresholds, confidence rules and impact scoring.

The supported branches still need representative bounded aggregate calls and result completeness checks before end-to-end acceptance. Metadata and SELECT 1 do not establish those. Optional browser/repository/ticket operations remain independent.
