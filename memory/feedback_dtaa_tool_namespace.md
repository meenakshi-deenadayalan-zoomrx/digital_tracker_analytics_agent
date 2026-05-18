---
name: Use mcp__dtsa__ for DTAA analytics queries
description: For DTAA analytics work (SOV, Reach, Frequency, Share of Attention), always use mcp__dtsa__dtsa_mysql_read — not mcp__dtsa-tools__dtsa_mysql_read
type: feedback
originSessionId: 0c3b4239-7438-462d-85e3-1ef5aba429ae
---
Use `mcp__dtsa__dtsa_mysql_read` (DTAA tool namespace) for all analytics queries, not `mcp__dtsa-tools__dtsa_mysql_read` (DTSA diagnostic tool namespace).

**Why:** The DTAA agent has its own MCP tool namespace (`mcp__dtsa__*`). Using the DTSA tools (`mcp__dtsa-tools__*`) for analytics work is incorrect — those are for the diagnostic agent.

**How to apply:** Any time a DTAA skill (dtaa, dtaa-ads-metrics, dtaa-web-metrics, etc.) needs to run a SQL query, load and call `mcp__dtsa__dtsa_mysql_read`, not `mcp__dtsa-tools__dtsa_mysql_read`.
