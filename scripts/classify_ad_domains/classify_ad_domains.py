"""Reusable pipeline to find non-healthcare ad destination domains for the ignore list.

Subcommands (run in order):
  schema     Discover ads table + ignore-list table columns.
  extract    Pull unique destination-url domains (last N months), minus existing
             ignore list, into state/domains.json. Uses keyset pagination so it
             handles 10k+ rows without OOM.
  heuristic  Apply Tier A curated allowlist (obvious non-healthcare brands/TLDs).
  next       Print next batch of un-classified domains as JSON (for Claude to
             classify via WebFetch/WebSearch).
  submit     Accept a JSON file of classifications and merge into state.
  report     Emit ignore_candidates.md + ignore_list_additions.txt.

State lives in ./state/ and is resumable. Safe to stop/restart at any point.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text  # noqa: E402

from dtsa_database import get_extension_read_db  # noqa: E402

STATE_DIR = Path(__file__).parent / "state"
STATE_DIR.mkdir(exist_ok=True)

DOMAINS_FILE = STATE_DIR / "domains.json"         # {domain: {first_seen_url, count, classification, confidence, evidence}}
SCHEMA_FILE = STATE_DIR / "schema.json"
CONFIG_FILE = Path(__file__).parent / "config.json"  # user-editable: table names, column names

DEFAULT_CONFIG = {
    "ads_table": "ads",
    "ads_url_column": "destination_url",
    "ads_created_column": "created",
    "ads_status_column": "status",
    "status_skip_value": "NOT_REQUIRED",
    "ignore_list_table": "ad_ignorelist_domains",
    "ignore_list_domain_column": "name",
    "ignore_list_active_column": "is_active",
    "lookback_months": 6,
}

# ---------------------------------------------------------------------------
# Tier A: curated non-healthcare domains / patterns.
# These are well-known brands where we are 100% confident the destination is
# not pharma/healthcare content. Keep additions conservative — the goal is
# zero false positives.
# ---------------------------------------------------------------------------
TIER_A_NON_HEALTHCARE = {
    # Retail / ecommerce
    "amazon.com", "amazon.co.uk", "ebay.com", "walmart.com", "target.com",
    "bestbuy.com", "etsy.com", "aliexpress.com", "shein.com", "temu.com",
    "costco.com", "homedepot.com", "lowes.com", "ikea.com", "wayfair.com",
    # Streaming / media / social
    "netflix.com", "hulu.com", "disneyplus.com", "spotify.com", "youtube.com",
    "tiktok.com", "facebook.com", "instagram.com", "twitter.com", "x.com",
    "reddit.com", "pinterest.com", "linkedin.com", "snapchat.com",
    # Travel
    "expedia.com", "booking.com", "airbnb.com", "tripadvisor.com", "kayak.com",
    "united.com", "delta.com", "southwest.com", "marriott.com", "hilton.com",
    # Finance / crypto (non-health)
    "chase.com", "bankofamerica.com", "wellsfargo.com", "capitalone.com",
    "paypal.com", "venmo.com", "robinhood.com", "coinbase.com", "binance.com",
    # Food / delivery
    "doordash.com", "ubereats.com", "grubhub.com", "instacart.com",
    "mcdonalds.com", "starbucks.com", "dominos.com", "chipotle.com",
    # Auto
    "ford.com", "toyota.com", "honda.com", "tesla.com", "carvana.com",
    "kbb.com", "edmunds.com", "cargurus.com", "autotrader.com",
    # Tech / SaaS (non-health)
    "microsoft.com", "apple.com", "google.com", "adobe.com", "slack.com",
    "zoom.us", "dropbox.com", "github.com", "openai.com",
    # News / sports / entertainment
    "cnn.com", "foxnews.com", "nytimes.com", "espn.com", "bleacherreport.com",
    "imdb.com", "rottentomatoes.com",
}

# Ad-tech infra domains — these appear as destination_url because of redirect
# chains / tracking pixels, not real landing pages. Never healthcare content.
TIER_A_ADTECH_INFRA = {
    "doubleclick.net", "googlesyndication.com", "googleadservices.com",
    "2mdn.net", "adsrvr.org", "adnxs.com", "rubiconproject.com", "openx.net",
    "pubmatic.com", "bidswitch.net", "mathtag.com", "serving-sys.com",
    "360yield.com", "smartadserver.com", "criteo.com", "taboola.com",
    "outbrain.com", "casalemedia.com", "contextweb.com", "liadm.com",
    "adform.net", "stickyadstv.com", "revcontent.com", "yieldmo.com",
    "smaato.com", "indexexchange.com", "beeswax.com", "media.net",
    "conversantmedia.com", "onetag-sys.com", "bluekai.com", "adtechus.com",
    "rlcdn.com", "everesttech.net", "demdex.net", "bizographics.com",
    "adlightning.com", "quantserve.com", "scorecardresearch.com",
    "bidtheatre.com", "yandex.ru", "go-mpulse.net",
}

# Known pharma / biotech corporate domains. ANY subdomain (or the bare domain)
# resolves to healthcare content — branded drug sites, HCP portals, PI docs.
TIER_A_PHARMA_CORPS = {
    "lilly.com", "pfizer.com", "pfizerpro.com", "merck.com", "merckconnect.com",
    "novartis.com", "astrazeneca.com", "gsk.com", "gskpro.com", "bms.com",
    "abbvie.com", "abbviepro.com", "jnj.com", "janssen.com", "janssenmd.com",
    "roche.com", "genentech.com", "gene.com", "bayer.com", "sanofi.com",
    "gilead.com", "gileadhcp.com", "regeneron.com", "biogen.com",
    "boehringer-ingelheim.com", "vertex.com", "vrtx.com", "modernatx.com",
    "takeda.com", "takedaoncology.com", "otsuka.com", "otsuka-us.com",
    "servier.com", "ucb.com", "daiichisankyo.com", "daiichi-sankyo.com",
    "teva.com", "tevausa.com", "lundbeck.com", "mallinckrodt.com",
    "astellas.com", "alkermes.com", "alnylam.com", "amgen.com",
    "bristol.com", "bms-hcp.com", "biomarin.com", "incyte.com",
    "ipsen.com", "eisai.com", "novonordisk.com", "novocare.com",
    "novomedlink.com", "organon.com", "organonpro.com", "haleon.com",
    "kenvue.com", "bausch.com", "salixsalesaid.com", "viatris.com",
    "viatrispro.com", "mylan.com", "sunpharma.com", "drreddys.com",
    "emdserono.com", "emdgroup.com", "baxter.com", "medtronic.com",
    "abbott.com", "stryker.com", "horizontherapeutics.com",
    "alexion.com", "ionis.com", "sarepta.com",
}

# Healthcare publishers / HCP media / EHR / payer / gov.
TIER_A_HEALTHCARE_KNOWN = {
    "medscape.com", "medpagetoday.com", "mdalert.com", "prescriberpoint.com",
    "practicefusion.com", "epic.com", "cerner.com", "athenahealth.com",
    "doximity.com", "sermo.com", "webmd.com", "healthline.com",
    "mayoclinic.org", "clevelandclinic.org", "nih.gov", "fda.gov", "cdc.gov",
    "cms.gov", "medicare.gov", "medicaid.gov", "nejm.org", "jamanetwork.com",
    "thelancet.com", "bmj.com", "nature.com", "sciencedirect.com",
    "pubmed.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov", "drugs.com", "rxlist.com",
    "goodrx.com", "walgreens.com", "cvs.com", "riteaid.com",
    "caremark.com", "expressscripts.com", "optumrx.com",
}

# Suffix patterns on the full host (not registrable). If host matches, it's
# a branded HCP drug site (e.g. foo-hcp.com, fooxhcp.com).
PHARMA_HCP_SUFFIX_PATTERNS = ("hcp.com", "hcp.net", "hcp.org", "-hcp.com", "pro.com", "formd.com", "fordoctors.com")

# Keywords that strongly suggest a healthcare context when found on the page.
HEALTHCARE_KEYWORDS = {
    "patient", "physician", "hcp", "healthcare professional", "prescribing",
    "prescription", "rx", "pharma", "pharmaceutical", "clinical trial",
    "indication", "dosage", "medication", "therapy", "treatment", "disease",
    "diagnosis", "oncology", "cardiology", "diabetes", "immunology",
    "medicare", "medicaid", "fda", "side effects", "adverse events",
    "clinical study", "drug information",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_config() -> dict:
    if CONFIG_FILE.exists():
        return {**DEFAULT_CONFIG, **json.loads(CONFIG_FILE.read_text())}
    CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
    return dict(DEFAULT_CONFIG)


def load_domains() -> dict:
    if DOMAINS_FILE.exists():
        return json.loads(DOMAINS_FILE.read_text())
    return {}


def save_domains(d: dict) -> None:
    DOMAINS_FILE.write_text(json.dumps(d, indent=2, sort_keys=True))


def extract_domain(url: str) -> str | None:
    if not url:
        return None
    try:
        if "://" not in url:
            url = "http://" + url
        host = urlparse(url).hostname
        if not host:
            return None
        host = host.lower().lstrip(".")
        # Strip common subdomain noise
        if host.startswith("www."):
            host = host[4:]
        if host.startswith("m."):
            host = host[2:]
        return host or None
    except Exception:
        return None


def registrable(host: str) -> str:
    """Return second-level domain (naive — good enough for matching allowlists)."""
    parts = host.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------
def cmd_schema(args) -> None:
    cfg = load_config()
    out = {"generated_at": datetime.utcnow().isoformat()}
    with get_extension_read_db() as s:
        ads_cols = s.execute(text(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = :t ORDER BY ordinal_position"
        ), {"t": cfg["ads_table"]}).fetchall()
        out["ads_columns"] = [dict(column_name=r[0], data_type=r[1], nullable=r[2]) for r in ads_cols]

        candidates = s.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND (table_name LIKE '%ignore%' OR table_name LIKE '%blocklist%' OR table_name LIKE '%blacklist%' OR table_name LIKE '%skip%')"
        )).fetchall()
        out["ignore_table_candidates"] = [r[0] for r in candidates]

        if cfg.get("ignore_list_table"):
            ig_cols = s.execute(text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = DATABASE() AND table_name = :t ORDER BY ordinal_position"
            ), {"t": cfg["ignore_list_table"]}).fetchall()
            out["ignore_list_columns"] = [dict(column_name=r[0], data_type=r[1]) for r in ig_cols]

    SCHEMA_FILE.write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str))
    print(f"\nSaved -> {SCHEMA_FILE}")
    if not cfg.get("ignore_list_table") and out["ignore_table_candidates"]:
        print(f"\nSet ignore_list_table in {CONFIG_FILE} to one of: {out['ignore_table_candidates']}")


# ---------------------------------------------------------------------------
# extract — SQL-side host extraction + GROUP BY (one query, pulls unique hosts)
# ---------------------------------------------------------------------------
def cmd_extract(args) -> None:
    cfg = load_config()
    domains = load_domains()

    existing_ignore: set[str] = set()
    if cfg.get("ignore_list_table"):
        active_col = cfg.get("ignore_list_active_column")
        where = f"WHERE {active_col} = 1" if active_col else ""
        with get_extension_read_db() as s:
            rows = s.execute(text(
                f"SELECT {cfg['ignore_list_domain_column']} FROM {cfg['ignore_list_table']} {where}"
            )).fetchall()
            existing_ignore = {r[0].lower().lstrip(".") for r in rows if r[0]}
        print(f"Loaded {len(existing_ignore)} domains from existing ignore list")

    url_col = cfg["ads_url_column"]
    status_col = cfg["ads_status_column"]
    created_col = cfg["ads_created_column"]
    table = cfg["ads_table"]
    lookback = cfg["lookback_months"]
    skip_val = cfg["status_skip_value"]

    # Extract host in SQL:
    #   1. SUBSTRING_INDEX(url, '://', -1)   strip scheme (if any)
    #   2. SUBSTRING_INDEX(..., '/', 1)       take up to first '/'
    #   3. SUBSTRING_INDEX(..., '?', 1)       drop query if no path
    #   4. SUBSTRING_INDEX(..., ':', 1)       drop port
    #   5. LOWER                              normalize case
    # www./m. prefix stripping is done in Python after fetch.
    host_expr = (
        f"LOWER(SUBSTRING_INDEX(SUBSTRING_INDEX(SUBSTRING_INDEX("
        f"SUBSTRING_INDEX({url_col}, '://', -1), '/', 1), '?', 1), ':', 1))"
    )

    query = text(f"""
        SELECT {host_expr} AS host,
               COUNT(*) AS cnt,
               MIN({url_col}) AS sample_url
          FROM {table}
         WHERE {created_col} >= DATE_SUB(NOW(), INTERVAL :months MONTH)
           AND {status_col} != :skip_val
           AND {url_col} IS NOT NULL
           AND {url_col} != ''
         GROUP BY host
    """)

    print("Running SQL-side GROUP BY (this may take a few minutes for ~1M rows)...")
    with get_extension_read_db() as s:
        s.execute(text("SET SESSION MAX_EXECUTION_TIME=600000"))  # 10 min
        rows = s.execute(query, {"months": lookback, "skip_val": skip_val}).fetchall()

    print(f"Got {len(rows)} raw host groups from DB. Normalizing...")

    new_domains = 0
    skipped_ignored = 0
    for raw_host, cnt, sample_url in rows:
        if not raw_host:
            continue
        # normalize www./m. prefix, re-merge any collisions
        host = raw_host.lstrip(".")
        if host.startswith("www."):
            host = host[4:]
        elif host.startswith("m."):
            host = host[2:]
        if not host or "." not in host:
            continue
        if host in existing_ignore or registrable(host) in existing_ignore:
            skipped_ignored += 1
            continue
        entry = domains.get(host)
        if entry is None:
            domains[host] = {
                "count": int(cnt),
                "first_seen_url": (sample_url or "")[:500],
                "classification": None,
                "confidence": None,
                "evidence": None,
            }
            new_domains += 1
        else:
            # merge (www vs bare variants collapse to same key)
            entry["count"] += int(cnt)

    save_domains(domains)
    print(f"\nDone.")
    print(f"  Unique domains (post-normalize): {len(domains)}")
    print(f"  New this run:                    {new_domains}")
    print(f"  Skipped (already on ignore list): {skipped_ignored}")


# ---------------------------------------------------------------------------
# heuristic — Tier A
# ---------------------------------------------------------------------------
def cmd_heuristic(args) -> None:
    domains = load_domains()
    stats = {"non_healthcare": 0, "healthcare": 0, "adtech_infra": 0}
    for host, entry in domains.items():
        if entry.get("classification"):
            continue
        reg = registrable(host)

        # --- non-healthcare: curated brand allowlist
        if host in TIER_A_NON_HEALTHCARE or reg in TIER_A_NON_HEALTHCARE:
            entry.update(classification="non_healthcare", confidence="high",
                         evidence=f"Curated non-healthcare brand (match: {reg})")
            stats["non_healthcare"] += 1
            continue

        # --- adtech infra (never a real landing page)
        if host in TIER_A_ADTECH_INFRA or reg in TIER_A_ADTECH_INFRA:
            entry.update(classification="non_healthcare", confidence="high",
                         evidence=f"Ad-tech infrastructure domain (match: {reg})")
            stats["adtech_infra"] += 1
            continue

        # --- healthcare: known HCP/pharma/gov/media
        if host in TIER_A_HEALTHCARE_KNOWN or reg in TIER_A_HEALTHCARE_KNOWN:
            entry.update(classification="healthcare", confidence="high",
                         evidence=f"Known healthcare brand (match: {reg})")
            stats["healthcare"] += 1
            continue

        # --- healthcare: pharma corp (any subdomain)
        pharma_match = None
        if reg in TIER_A_PHARMA_CORPS:
            pharma_match = reg
        else:
            for corp in TIER_A_PHARMA_CORPS:
                if host.endswith("." + corp) or host == corp:
                    pharma_match = corp
                    break
        if pharma_match:
            entry.update(classification="healthcare", confidence="high",
                         evidence=f"Pharma corporate domain (match: {pharma_match})")
            stats["healthcare"] += 1
            continue

        # --- healthcare: branded HCP suffix pattern (e.g. foo-hcp.com, barhcp.com)
        hcp_hit = None
        for suf in PHARMA_HCP_SUFFIX_PATTERNS:
            if reg.endswith(suf) and reg != suf:
                hcp_hit = suf
                break
        if hcp_hit:
            entry.update(classification="healthcare", confidence="high",
                         evidence=f"Branded HCP-suffix pattern (ends with '{hcp_hit}')")
            stats["healthcare"] += 1
            continue

    save_domains(domains)
    total = sum(stats.values())
    print(f"Heuristic pass marked {total} domains: {stats}")
    _print_status(domains)


# ---------------------------------------------------------------------------
# next / submit — for Claude-driven classification
# ---------------------------------------------------------------------------
def cmd_next(args) -> None:
    domains = load_domains()
    pending = [
        {"domain": h, "count": e["count"], "sample_url": e["first_seen_url"]}
        for h, e in domains.items()
        if not e.get("classification") and e["count"] >= args.min_count
    ]
    pending.sort(key=lambda x: -x["count"])  # high-traffic first
    chunk = pending[: args.batch_size]
    print(json.dumps({
        "batch_size": len(chunk),
        "remaining": len(pending) - len(chunk),
        "min_count_filter": args.min_count,
        "domains": chunk,
        "healthcare_keywords": sorted(HEALTHCARE_KEYWORDS),
        "instructions": (
            "For each domain: WebFetch https://<domain>/ with prompt 'Is this a "
            "healthcare, pharma, medical, HCP, or patient site? Quote any evidence.' "
            "Classify as 'non_healthcare' (confidence high/medium/low), 'healthcare', "
            "or 'uncertain'. Only 'non_healthcare' with confidence 'high' will be "
            "added to the ignore list. Submit via: python classify_ad_domains.py "
            "submit results.json"
        ),
    }, indent=2))


def cmd_submit(args) -> None:
    data = json.loads(Path(args.file).read_text())
    domains = load_domains()
    updated = 0
    for item in data:
        host = item["domain"].lower().lstrip(".")
        if host not in domains:
            continue
        domains[host].update(
            classification=item.get("classification"),
            confidence=item.get("confidence"),
            evidence=item.get("evidence"),
        )
        updated += 1
    save_domains(domains)
    print(f"Updated {updated} domains.")
    _print_status(domains)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def cmd_report(args) -> None:
    domains = load_domains()
    md_lines = [
        "# Ad Destination Domain Classification Report",
        f"\nGenerated: {datetime.utcnow().isoformat()}",
        f"Total unique domains analyzed: {len(domains)}\n",
        "## 100% Confident Non-Healthcare (add to ignore list)\n",
        "| Domain | Count | Evidence |",
        "|--------|-------|----------|",
    ]
    ignore_additions: list[str] = []
    uncertain: list[tuple[str, dict]] = []
    healthcare: list[tuple[str, dict]] = []

    for host, e in sorted(domains.items(), key=lambda kv: -kv[1]["count"]):
        cls = e.get("classification")
        conf = e.get("confidence")
        if cls == "non_healthcare" and conf == "high":
            md_lines.append(f"| `{host}` | {e['count']} | {e.get('evidence', '')} |")
            ignore_additions.append(host)
        elif cls == "healthcare":
            healthcare.append((host, e))
        elif not cls or conf in (None, "low", "medium") or cls == "uncertain":
            uncertain.append((host, e))

    md_lines += [
        f"\n**Total additions: {len(ignore_additions)}**\n",
        "## Healthcare / Pharma (keep processing)\n",
        "| Domain | Count | Evidence |",
        "|--------|-------|----------|",
    ]
    for host, e in healthcare[:200]:
        md_lines.append(f"| `{host}` | {e['count']} | {e.get('evidence', '')} |")

    md_lines += [
        f"\n**Total healthcare domains: {len(healthcare)}**\n",
        "## Needs Human Review (uncertain / low confidence)\n",
        "| Domain | Count | Classification | Confidence | Evidence |",
        "|--------|-------|----------------|------------|----------|",
    ]
    for host, e in uncertain[:500]:
        md_lines.append(
            f"| `{host}` | {e['count']} | {e.get('classification') or '—'} "
            f"| {e.get('confidence') or '—'} | {e.get('evidence', '')} |"
        )

    out_md = Path(args.output or (STATE_DIR / "ignore_candidates.md"))
    out_list = Path(args.list_output or (STATE_DIR / "ignore_list_additions.txt"))
    out_md.write_text("\n".join(md_lines))
    out_list.write_text("\n".join(ignore_additions) + "\n")
    print(f"Wrote {out_md}")
    print(f"Wrote {out_list} ({len(ignore_additions)} domains)")


def _print_status(domains: dict) -> None:
    total = len(domains)
    classified = sum(1 for e in domains.values() if e.get("classification"))
    high_conf_non_hc = sum(
        1 for e in domains.values()
        if e.get("classification") == "non_healthcare" and e.get("confidence") == "high"
    )
    print(f"Status: {classified}/{total} classified | {high_conf_non_hc} confirmed non-healthcare (high confidence)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("schema").set_defaults(func=cmd_schema)

    sub.add_parser("extract").set_defaults(func=cmd_extract)

    sub.add_parser("heuristic").set_defaults(func=cmd_heuristic)

    nx = sub.add_parser("next")
    nx.add_argument("--batch-size", type=int, default=50)
    nx.add_argument("--min-count", type=int, default=10,
                    help="Skip domains with count <= this (default: 10)")
    nx.set_defaults(func=cmd_next)

    sb = sub.add_parser("submit")
    sb.add_argument("file")
    sb.set_defaults(func=cmd_submit)

    rp = sub.add_parser("report")
    rp.add_argument("--output")
    rp.add_argument("--list-output")
    rp.set_defaults(func=cmd_report)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
