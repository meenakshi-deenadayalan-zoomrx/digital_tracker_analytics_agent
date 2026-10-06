"""Actives Query across Channel - run the team's standard actives query for a
supplied target list (TL) of NPIs. See references/actives_across_channel.md.

Usage:
  python actives_across_channel.py --tl npis.csv --start 2026-01-01 --end 2026-06-30 --out out.csv
  python actives_across_channel.py --tl npis.csv --start ... --end ... --sql query.sql   # emit SQL only
"""
import argparse
import csv
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

COMMON = """LEFT JOIN project_target_list AS ptl ON u.npi = ptl.npi
LEFT JOIN projects AS pr ON ptl.project_id = pr.id
LEFT JOIN user_speciality_mappings AS usm ON usm.user_id = {uid}
LEFT JOIN specialities AS spec ON spec.id = speciality_id"""


def sel(ts, uid, typ):
    return (
        "SELECT DISTINCT clients.id AS client_id, clients.device_platform, pr.name,\n"
        f"    {uid} AS user_id, u.npi, speciality,\n"
        f"    CONCAT(MONTH({ts}), '-', YEAR({ts})) AS period,\n"
        f"    CONCAT('Q', QUARTER({ts}), '''', DATE_FORMAT({ts}, '%y')) AS quarter_year,\n"
        f"    '{typ}' AS type"
    )


BRANCHES = {
    "WEB_PAGE": sel("w.created", "w.user_id", "WEB_PAGE") + f"""
FROM web_contents AS w
INNER JOIN users AS u ON w.user_id = u.id
{COMMON.format(uid="w.user_id")}
INNER JOIN tracked_urls AS t ON t.id = w.tracked_url_id
INNER JOIN clients ON clients.id = w.client_id
WHERE w.type IN ('WEB_PAGE','HTML_WEB_PAGE') AND w.user_wave_id IS NULL
  AND w.created BETWEEN '{{S}}' AND '{{E}}'
  AND spec.id NOT IN (28,30) AND u.npi IN ({{N}})""",
    "EMAIL": sel("w.created", "w.user_id", "EMAIL") + f"""
FROM web_contents AS w
INNER JOIN users AS u ON w.user_id = u.id
{COMMON.format(uid="w.user_id")}
LEFT JOIN clients ON clients.id = w.client_id
WHERE w.type = 'EMAIL_CAMPAIGN'
  AND w.created BETWEEN '{{S}}' AND '{{E}}'
  AND spec.id NOT IN (28,30) AND u.npi IN ({{N}})""",
    "ADS": sel("a.created", "a.user_id", "ADS") + f"""
FROM ads AS a
LEFT JOIN web_contents AS w ON w.id = a.web_content_id
INNER JOIN users AS u ON a.user_id = u.id
{COMMON.format(uid="a.user_id")}
INNER JOIN clients ON clients.id = a.client_id
WHERE a.created BETWEEN '{{S}}' AND '{{E}}'
  AND (w.type != 'EMAIL_CAMPAIGN' OR w.type IS NULL) AND a.user_wave_id IS NULL
  AND spec.id NOT IN (28,30) AND u.npi IN ({{N}})""",
    "POSTS": sel("wcp.created", "w.user_id", "POSTS") + f"""
FROM web_content_posts AS wcp
INNER JOIN web_contents AS w ON w.id = wcp.web_content_id
INNER JOIN users AS u ON w.user_id = u.id
{COMMON.format(uid="w.user_id")}
INNER JOIN clients ON clients.id = w.client_id
WHERE wcp.created BETWEEN '{{S}}' AND '{{E}}'
  AND spec.id NOT IN (28,30) AND w.user_wave_id IS NULL AND u.npi IN ({{N}})""",
    "SEARCH_ADS": sel("sa.created", "sq.user_id", "SEARCH_ADS") + f"""
FROM search_queries AS sq
INNER JOIN search_results AS sa ON sa.search_query_id = sq.id AND sa.type = 'SPONSORED_AD'
INNER JOIN users AS u ON sq.user_id = u.id
{COMMON.format(uid="sq.user_id")}
INNER JOIN clients ON clients.id = sq.client_id
WHERE sa.created BETWEEN '{{S}}' AND '{{E}}'
  AND spec.id NOT IN (28,30) AND sq.user_wave_id IS NULL AND u.npi IN ({{N}})""",
    "AI_Overview/Mode": sel("ar.created", "sq.user_id", "AI_Overview/Mode") + f"""
FROM search_queries AS sq
INNER JOIN ai_responses AS ar ON ar.search_query_id = sq.id
INNER JOIN users AS u ON sq.user_id = u.id
{COMMON.format(uid="sq.user_id")}
INNER JOIN clients ON clients.id = sq.client_id
WHERE ar.created BETWEEN '{{S}}' AND '{{E}}'
  AND spec.id NOT IN (28,30) AND sq.user_wave_id IS NULL AND u.npi IN ({{N}})""",
}


def load_npis(path):
    npis = set()
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            npis.update(re.findall(r"\b\d{10}\b", line))
    return sorted(npis)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tl", required=True, help="file with NPIs (one per line / any column)")
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD (inclusive)")
    ap.add_argument("--out", help="CSV output path")
    ap.add_argument("--sql", help="write the inlined SQL here instead of running it")
    a = ap.parse_args()
    if not (a.out or a.sql):
        ap.error("need --out or --sql")

    npis = load_npis(a.tl)
    print(f"NPIs in TL: {len(npis)}", flush=True)
    S, E = f"{a.start} 00:00:00", f"{a.end} 23:59:59"

    if a.sql:
        N = ",\n".join(", ".join(npis[i:i + 20]) for i in range(0, len(npis), 20))
        header = (f"-- Actives across all channels, {a.start} to {a.end}, "
                  f"{len(npis)} NPIs from {os.path.basename(a.tl)}\n\n")
        body = "\n\nUNION ALL\n\n".join(b.format(S=S, E=E, N="\n" + N + "\n") for b in BRANCHES.values())
        with open(a.sql, "w", encoding="utf-8") as f:
            f.write(header + body + ";\n")
        print(f"wrote {a.sql}")
        return

    sys.path.insert(0, REPO)
    from sqlalchemy import text
    from dtsa_database import get_extension_read_db

    N = ",".join(npis)
    with open(a.out, "w", newline="", encoding="utf-8") as f, get_extension_read_db() as s:
        in_panel = s.execute(text(f"SELECT COUNT(DISTINCT npi) FROM users WHERE npi IN ({N})")).scalar()
        excl = s.execute(text(
            "SELECT COUNT(DISTINCT u.id) FROM users u JOIN user_speciality_mappings m ON m.user_id=u.id "
            f"WHERE u.npi IN ({N}) AND m.speciality_id IN (28,30)")).scalar()
        print(f"NPIs in users table: {in_panel}; in excluded specialities 28/30: {excl}", flush=True)
        w = csv.writer(f)
        hdr = False
        for name, q in BRANCHES.items():
            t = time.time()
            r = s.execute(text(q.format(S=S, E=E, N=N)))
            if not hdr:
                w.writerow(r.keys())
                hdr = True
            rows = r.fetchall()
            w.writerows(rows)
            distinct = len({row[4] for row in rows})
            print(f"{name}: {len(rows)} rows, {distinct} distinct NPIs ({time.time() - t:.0f}s)", flush=True)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
