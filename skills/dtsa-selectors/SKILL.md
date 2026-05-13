---
name: "DTSA Selector Validation"
description: "Test CSS and XPath selectors against live web pages using Playwright. Activate when investigating selector breaks, DOM restructures, or content script injection failures for email, search_results, or ads channels."
---

# Selector Validation

Use `dtsa_playwright_selector` to test selectors against live pages.

## Tool Parameters

- `url`: the page URL to test
- `selector`: CSS or XPath selector string
- `selector_type`: `css` (default) or `xpath`

## When to Run

Run for DOM-dependent channels: **email**, **search_results**, **ads**.
Skip for `web_contents` and `social_posts` unless specifically suspected.

## Testing Protocol

1. Read `references/selector_inventory.md` for the selector to test
2. Test the primary selector first
3. If it fails, test secondary selectors to distinguish:
   - **All selectors fail** → full provider DOM restructure (redesign)
   - **One selector fails** → targeted element change
4. If bot detection triggers → record INCONCLUSIVE, do not retry or attempt bypass

## Result Interpretation

| Result | Meaning | Next step |
|---|---|---|
| `found: true, element_count > 0` | Selector works — issue is elsewhere | Proceed to commit analysis |
| `found: false, element_count: 0` | **Selector broken** — DOM likely changed | CONFIRMED evidence; check commits for selector change |
| `blocked: true` | Bot detection — INCONCLUSIVE | Record and proceed without selector evidence |
| `error: "Navigation failed"` | Page unreachable | Network/URL issue — try alternate URL |

## After a Broken Selector

Use `dtsa_grep_repo` to find the current selector definition in code:
```
dtsa_grep_repo(repo="digitrace-chrome-extension", pattern="h2\\.hP")
```

Use `dtsa_read_file` to read the full content script to understand context and propose a fix.

See `references/selector_inventory.md` for all known selectors by channel and provider.
