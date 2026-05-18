---
name: Use inline literals not %(param)s in CASE WHEN REGEXP queries
description: %(param)s parameterization fails for REGEXP expressions inside CASE WHEN in dtsa_mysql_read
type: feedback
originSessionId: 00f415b2-6687-4af7-9355-f3c71eb7b158
---
`dtsa_mysql_read` does not substitute `%(param)s` placeholders when they appear inside `CASE WHEN ... REGEXP %(param)s` expressions. MySQL receives the literal `%(param)s` string and throws a syntax error (1064).

**Why:** The MySQL connector's parameter substitution does not work in this context with the tool's implementation.

**How to apply:** Always hardcode regex patterns and other values directly as string literals in the SQL. Do not use `%(param)s` placeholders for values used inside REGEXP expressions in CASE WHEN statements. Use parameterization only for simple scalar values like project_id if needed, but when in doubt, use inline literals throughout.
