# Brand Normalization

Fills the `{brand_normalization}` placeholder in the SOV templates.

`brand_terms` holds multiple rows for the same drug — OCR errors and data-entry
variations. Without normalization, SOV fragments across those duplicates and each
variant reports a fraction of the brand's true share.

Apply the `CASE WHEN` in the **inner `cn` subquery**, inside the
`GROUP_CONCAT(DISTINCT CASE ... END)` that builds `brand_name`. In the standard
SOV template that means the `au`, `tb`, and `uba` subqueries — **not** `uta`,
which has no `brand_name`.

Hardcode the regex as a string literal. `%(param)s` does not substitute inside
`CASE WHEN ... REGEXP` — see the inline-literals rule in `guidelines.md`.

## Template

```sql
CASE
  WHEN LOWER(bt.standard_name) REGEXP '^keytruda$|^pembrolizumab$|^pembrolizumab-x$|^keytruda sc$|^subcutaneous keytruda$|^subcutaneous pembrolizumab$|^keytruda hyaluronidase|^keytrudaqlex$' THEN 'Keytruda'
  WHEN LOWER(bt.standard_name) REGEXP '^vylo|zolbetuximab' THEN 'VYLOY'
  ELSE bt.standard_name
END AS brand_name
```

## Rules

### Keytruda (pembrolizumab)

Normalize to `'Keytruda'`.

```
^keytruda$|^pembrolizumab$|^pembrolizumab-x$|^keytruda sc$|^subcutaneous keytruda$|^subcutaneous pembrolizumab$|^keytruda hyaluronidase|^keytrudaqlex$
```

The anchors matter. Combination therapies — `keytruda + lenvima`,
`keytruda; inlyta` — are **distinct products** and must stay separate. They
contain `;`, `+`, `/`, or `,`, and the anchored patterns above already exclude
them. Do not loosen to `^keytruda` or you will silently fold combos into the
monotherapy total.

### VYLOY (zolbetuximab)

Normalize to `'VYLOY'`.

```
^vylo|zolbetuximab
```

Covers VYLOY, Vylo, Vyloi, Vylovy, vylov, vyloma, Vyloyi, Vyloyo, Vyloyy,
Zolbetuximab, zolbetuximab-clzb. Every `^vylo*` variant is an OCR or annotation
error for the same drug — unlike Keytruda, there is no combo ambiguity here, so
the unanchored prefix is safe.

## Adding a new brand

Before adding a rule, confirm the variants are genuinely the same product:

```sql
SELECT bt.standard_name, COUNT(*) AS n
FROM brand_terms bt
WHERE LOWER(bt.standard_name) REGEXP '<candidate pattern>'
GROUP BY bt.standard_name
ORDER BY n DESC
```

Read the full list before writing the pattern. Check for combination therapies
(`;`, `+`, `/`, `,`) and anchor the regex if any appear. A too-broad pattern
overstates the brand and the error is invisible in the output — the SOV table
still sums to 100%.

Then add the rule here, so it applies to every channel rather than to one
session's query.

### CD19 CAR-T brands (Yescarta, Kymriah, Breyanzi)

Normalize generic/abbreviation rows to the brand. Verified 2026-11-11; the
`brand_terms` ids are stable so an id list is cheaper than REGEXP on the hot path.

```sql
WHEN bt.id IN (133, 24769, 24860)          THEN 'Yescarta'   -- Yescarta, Axi-Cel, axicabtagene ciloleucel
WHEN bt.id IN (29087, 30375, 47801)        THEN 'Kymriah'    -- kymriah, Tisa-cel, tisagenlecleucel
WHEN bt.id IN (202, 4399, 71228)           THEN 'Breyanzi'   -- Breyanzi, Lisocabtagene Maraleucel, Lisocabtagenemaraleucel
WHEN LOWER(bt.standard_name) = 'brevanzi'  THEN 'Breyanzi'   -- OCR variant seen in LBCL ads
```

Regex equivalent: `^yescarta$|^axi-cel$|^axicabtagene`, `^kymriah$|^tisa-cel$|^tisagenlecleucel$`,
`^bre[yv]anzi$|^lisocabtagene`. Anchored: `Breyanzi,Kymriah,Tecartus,Yescarta` combo
rows (class-comparison content) stay separate.

Note: these three are LBCL/other-lymphoma products. In MM they return ~0 rows; the
MM CAR-Ts are Carvykti (178, 4315, 87758) and Abecma (203).
