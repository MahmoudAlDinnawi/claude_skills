# Input Formats

The analyzer auto-detects most common formats. Run `python3 scripts/analyze.py --inspect <file>` first to see what columns it found.

## Supported file types

- `.csv` (UTF-8, with header row)
- `.xlsx` (requires `openpyxl`)
- `.json` (single object, list of objects, or Google Takeout)
- A folder containing any mix of the above (will be merged)

## Format-specific notes

### Google reviews JSON

This is the JSON shape produced by most Google review export tools — nested reviewer, word-form star ratings, ISO timestamps:

```json
{
  "reviews": [
    {
      "reviewer": {"displayName": "Ahmed Al-Mansoori"},
      "starRating": "FIVE",
      "comment": "Amazing food!",
      "createTime": "2025-02-14T19:30:00Z"
    }
  ]
}
```

The parser handles all of this automatically:
- Word ratings (`"FIVE"` → 5, `"FOUR"` → 4, …)
- Nested `reviewer.displayName` flattened
- `createTime` / `updateTime` recognized as date columns
- `(Translated by Google) ... (Original) ...` comments split — we keep the **original** Arabic per the skill rule

Just run:
```bash
python3 scripts/analyze.py --input google-reviews.json --output ./out --restaurant-name "X" --country SA
```

### Google reviews CSV export

CSV columns typically:

```
reviewer, starRating, comment, createTime, location
```

Same auto-detection applies. Word ratings and nested fields don't appear in CSV exports — only in JSON.

### Google Takeout (My Activity)

```
~/Downloads/Takeout/My Activity/Maps/MyActivity.json
```

The parser detects this format and filters non-review entries. Star ratings are often only embedded in the title text (`Rated 4 stars on …`) — the parser extracts them.

### TripAdvisor export

XLSX with columns like:
```
Title, Review, Rating, Date of stay, Trip type, Reviewer
```

Use:
```bash
--text-column "Review" --rating-column "Rating" --date-column "Date of stay"
```

### Talabat / HungerStation / Careem / Jahez

CSV typically:
```
order_id, branch, rating, comment, created_at
```

The `branch` column is critical for multi-location analysis. Auto-detected as a branch column. If your export uses a different column name:
```bash
--branch-column "outlet_name"
```

### Zomato

CSV often has:
```
review_id, rating, review_text, outlet, posted_at
```

Auto-detected. If you have a sentiment column already, the analyzer ignores it and re-classifies.

### Generic JSON

A list of objects works as-is:
```json
[
  {"text": "Great food!", "rating": 5, "date": "2026-01-15", "branch": "Riyadh - Olaya"},
  {"text": "بطيء جدا", "rating": 2, "date": "2026-01-16"}
]
```

Or an object wrapping the list:
```json
{"reviews": [...]}
```

## Column auto-detection

Names are normalized (lowercased, non-alphanumerics stripped) and matched case-insensitively against:

| Field | Accepted column names (any case, with/without underscores) |
|---|---|
| Rating | rating, stars, starRating, score, reviewRating, overallRating |
| Text | text, review, reviewText, comment, comments, feedback, body, message, content |
| Date | date, reviewDate, createdAt, timestamp, time, submittedAt |
| Branch | branch, outlet, location, store, restaurant, site, venue |
| Reviewer | reviewer, name, user, customer, author |

If your column is named something else entirely (e.g. `ملاحظات` for comment), pass it explicitly with `--text-column "ملاحظات"`.

## Date format detection

The parser tries these formats automatically:
- ISO: `2026-01-15`, `2026-01-15T14:30:00`, `2026-01-15T14:30:00.000Z`
- Slashed: `15/01/2026`, `01/15/2026`, `15-01-2026`
- Named month: `Jan 15, 2026`, `January 15, 2026`, `15 Jan 2026`, `15 January 2026`
- Epoch seconds or milliseconds (numeric)

If it can't parse a date, the record is still included but excluded from the trend chart.

## Rating scale

Default: 5-star scale. For NPS surveys with 0–10 ratings, pass `--rating-scale 10`.

The parser also handles strings like `4 out of 5` or `8/10` and normalizes to the chosen scale.

## Privacy

Many exports include reviewer names, emails, or phone numbers in free text. Before sharing the report:
1. Open `out/normalized.csv`
2. Search for `@` and digit patterns
3. Redact as needed before generating the final HTML report

The skill never uploads data anywhere — everything runs locally.
