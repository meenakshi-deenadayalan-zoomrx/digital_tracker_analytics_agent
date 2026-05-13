"""Group the 'confirmed non-healthcare' list into review categories.

Writes state/categorized_review.md with domains bucketed for spot-check before
importing into the ignore list.
"""
import json
import re
from pathlib import Path

STATE = Path(__file__).parent / "state"
domains = json.loads((STATE / "domains.json").read_text())

# Pull just confirmed non-healthcare + high confidence
items = [
    (h, e) for h, e in domains.items()
    if e.get("classification") == "non_healthcare" and e.get("confidence") == "high"
]
items.sort(key=lambda kv: -kv[1]["count"])


def reg(host: str) -> str:
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


# --- Category rules (first match wins) ---
PLATFORM_RISK = {
    "google.com", "youtube.com", "facebook.com", "instagram.com",
    "twitter.com", "x.com", "linkedin.com", "reddit.com", "tiktok.com",
    "pinterest.com", "snapchat.com", "cnn.com", "foxnews.com", "nytimes.com",
    "aol.com", "yahoo.com",
}

ADTECH_HINTS = (
    "doubleclick", "googlesyndication", "googleadservices", "2mdn", "adsrvr",
    "adnxs", "rubicon", "openx", "pubmatic", "bidswitch", "mathtag",
    "serving-sys", "360yield", "smartadserver", "criteo", "taboola",
    "outbrain", "casalemedia", "contextweb", "liadm", "adform",
    "stickyadstv", "revcontent", "yieldmo", "smaato", "indexexchange",
    "beeswax", "media.net", "conversantmedia", "onetag-sys", "bluekai",
    "adtechus", "rlcdn", "everesttech", "demdex", "bizographics",
    "adlightning", "quantserve", "scorecardresearch", "bidtheatre",
    "go-mpulse", "amazon-adsystem", "mediago", "seedtag", "adbutler",
)

RETAIL_HINTS = (
    "amazon.com", "walmart.com", "target.com", "bestbuy", "ebay", "etsy",
    "aliexpress", "shein", "temu", "costco", "homedepot", "lowes", "ikea",
    "wayfair", "allmodern", "rugs.com", "bindiusa", "urbani.com",
    "bowflex", "personalizationmall", "quill.com", "bjs.com",
    "moviesunlimited", "moxiplayer", "tmraudio", "puma", "ugg.com",
    "childrensplace", "forlest", "boody", "tedbaker", "zadig-et-voltaire",
    "milanolegacy", "cozzyhomes", "outbacktrading", "monos", "tryaladdin",
    "paganidesign", "marcobicego", "mubahy", "hazorfim", "virabyani",
    "zchocolat", "clinique", "valentino-beauty",
)

FINANCE_HINTS = (
    "chase.com", "bankofamerica", "wellsfargo", "capitalone", "paypal",
    "venmo", "robinhood", "coinbase", "binance", "experian", "mtb.com",
    "quicken", "chime.com", "avalara",
)

TRAVEL_HINTS = (
    "expedia", "booking.com", "airbnb", "tripadvisor", "kayak", "united.com",
    "delta.com", "southwest", "marriott", "hilton", "travelocity",
    "flytradewind", "deervalley", "skiidaho", "pendry", "tickets.la28",
)

FOOD_HINTS = (
    "doordash", "ubereats", "grubhub", "instacart", "mcdonalds", "starbucks",
    "dominos", "chipotle", "dosequis", "luckykitchen", "jjcrabhouse",
)

AUTO_HINTS = (
    "ford.com", "toyota.com", "honda.com", "tesla.com", "carvana",
    "kbb.com", "edmunds", "cargurus", "autotrader", "rangerover",
    "gmenvolve", "hankooktire", "carcover", "285motorsport",
    "store.carkeysexpress",
)

TECH_HINTS = (
    "microsoft.com", "apple.com", "adobe.com", "slack", "zoom.us",
    "dropbox", "github", "openai", "wpengine", "mailchimp",
    "webroot", "plaud.ai", "aionsilicon", "getjobber", "harvey.ai",
)

HOMEGOODS_HINTS = (
    "windownation", "carusohomes", "tripointehomes", "artisanpropertygroup",
    "voltlighting", "camfilapc", "arielbath", "msnrealty",
)


def categorize(host: str, reg_dom: str) -> str:
    if host in PLATFORM_RISK or reg_dom in PLATFORM_RISK:
        return "!! REVIEW — Major platform/search/social (pharma may advertise here)"
    for s in ADTECH_HINTS:
        if s in host:
            return "Adtech infrastructure"
    for s in RETAIL_HINTS:
        if s in host:
            return "Retail / ecommerce"
    for s in FINANCE_HINTS:
        if s in host:
            return "Finance / banking"
    for s in TRAVEL_HINTS:
        if s in host:
            return "Travel / hospitality"
    for s in FOOD_HINTS:
        if s in host:
            return "Food / restaurants"
    for s in AUTO_HINTS:
        if s in host:
            return "Automotive"
    for s in TECH_HINTS:
        if s in host:
            return "Tech / SaaS"
    for s in HOMEGOODS_HINTS:
        if s in host:
            return "Home / real estate / construction"
    return "Other / misc"


buckets: dict[str, list] = {}
for host, entry in items:
    cat = categorize(host, reg(host))
    buckets.setdefault(cat, []).append((host, entry))

# --- write markdown ---
lines = [
    "# Non-Healthcare Ignore-List Candidates — Categorized Review",
    f"\n{len(items)} domains classified non-healthcare / high confidence.\n",
    "**Review the `!! REVIEW` section first** — those are platforms where pharma sometimes lands ads.\n",
]

# Put REVIEW category first
order = sorted(buckets.keys(), key=lambda c: (not c.startswith("!!"), c))

for cat in order:
    rows = buckets[cat]
    lines.append(f"\n## {cat}  ({len(rows)} domains)\n")
    lines.append("| Domain | Count | Evidence |")
    lines.append("|--------|-------|----------|")
    for host, e in rows:
        lines.append(f"| `{host}` | {e['count']} | {e.get('evidence','')} |")

(STATE / "categorized_review.md").write_text("\n".join(lines))
print(f"Wrote {STATE / 'categorized_review.md'}")
print(f"\nCategory breakdown:")
for cat in order:
    print(f"  {len(buckets[cat]):>4}  {cat}")
