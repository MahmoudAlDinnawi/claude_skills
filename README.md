# Restaurant Feedback Analyzer — GCC Edition

> Turn restaurant customer feedback (Google reviews, Talabat, HungerStation, Zomato, TripAdvisor, Excel exports, JSON) into a polished, decision-ready HTML report — with first-class **Arabic + English** support and **GCC-specific themes** (halal, family section, prayer area, Ramadan iftar, shisha, dress code, delivery).

Built for restaurant operators, F&B consultants, and CX analysts working in **Saudi Arabia, UAE, Kuwait, Qatar, Bahrain, and Oman**.

---

## What you get

- **NPS, CSAT, CES, sentiment** computed correctly for star-rated reviews
- **Built-in guardrails** — small-sample warning (<30 ratings = NPS suppressed), missing-rating detection, single-location auto-handling
- **GCC theme tagging** — halal, family/singles section, prayer area, Ramadan, shisha, dress code, delivery, and 10+ more
- **Multi-format ingestion** — CSV, XLSX, JSON (incl. Google reviews shape with `"FIVE"`/`"FOUR"` ratings), Google Takeout, multi-file folders
- **Multi-branch analysis** — auto-aggregates per outlet when a branch column is detected
- **Bilingual** — Arabic reviews detected, kept in original RTL, analyzed without translation. `(Translated by Google)` boilerplate is stripped, original Arabic kept
- **Premium standalone HTML report** — animated charts, count-up KPIs, scroll-revealed sections, hover micro-interactions. Chart.js bundled, opens offline, prints to PDF cleanly

## How it looks

The output is a single `report.html` file with:
- Hero section with restaurant name, country, date range
- 4 KPI cards (NPS, CSAT, Avg Rating, Effort signal)
- NPS breakdown bar (promoters / passives / detractors)
- Rating distribution + monthly trend charts
- Sentiment + language mix donuts
- Theme cards with positive/negative split + sample quotes
- Per-branch comparison table
- GCC-specific callouts (Ramadan, halal, family, etc.)
- Strengths, issues with verbatim quotes, prioritized recommendations

---

## Install

```bash
git clone https://github.com/MahmoudAlDinnawi/claude_skills.git
cd claude_skills
pip install -r requirements.txt
```

## Usage

Run the scripts directly:

```bash
# 1. Inspect the file (optional, to confirm columns)
python3 scripts/analyze.py --inspect path/to/reviews.csv

# 2. Run analysis
python3 scripts/analyze.py \
  --input path/to/reviews.csv \
  --output ./out \
  --restaurant-name "Suhail Kitchen" \
  --country SA

# 3. (Optional) Hand-write narrative.json to populate strengths/issues/recs.
#    Schema: see SKILL.md.

# 4. Build the HTML
python3 scripts/build_report.py \
  --analysis out/analysis.json \
  --narrative out/narrative.json \
  --output out/report.html

# 5. Open it
open out/report.html        # macOS
xdg-open out/report.html    # Linux
```

## Try it on the samples

**CSV demo (36 multi-branch reviews, 3 months):**
```bash
python3 scripts/analyze.py \
  --input examples/sample-reviews.csv \
  --output out \
  --restaurant-name "Bayt Al Khaleej" \
  --country AE

python3 scripts/build_report.py \
  --analysis out/analysis.json \
  --narrative examples/sample-narrative.json \
  --output out/report.html

open out/report.html
```

**Google reviews JSON demo (20 reviews, mixed Arabic + English, small-sample warning shown):**
```bash
python3 scripts/analyze.py \
  --input examples/sample-google-reviews.json \
  --output out \
  --restaurant-name "Bayt Al Khaleej" \
  --country AE

python3 scripts/build_report.py \
  --analysis out/analysis.json \
  --narrative examples/sample-narrative-google.json \
  --output out/report.html

open out/report.html
```

---

## Why a GCC-specific tool?

Because generic CX platforms get GCC restaurant feedback wrong:

| Issue | Generic tools | This skill |
|---|---|---|
| Arabic reviews | Translated (badly) or dropped | Analyzed in original Arabic |
| Khaleeji dialect | Misread (`زفت` ≠ "tar") | Recognized as strong negative |
| Halal / prayer / family themes | Not in lexicon | First-class themes |
| Ramadan effects | Treated as outlier | Recognized + called out |
| Talabat / HungerStation | Ignored | Tagged as delivery cohort |
| 5★ → NPS conversion | Sometimes wrong | Industry-standard mapping |

GCC F&B NPS typically sits in the 20–40 range. Western dashboards that compare you to the 60+ benchmarks are noise.

---

## Supported input formats

No API access needed — everything is file-based.

- **Google reviews JSON** (the format used by most review-export tools — handles word-form ratings like `"FIVE"`, nested reviewer objects, and `(Translated by Google)` boilerplate)
- **Google reviews CSV** export
- **Google Takeout** `MyActivity.json`
- **TripAdvisor** XLSX export
- **Talabat / HungerStation / Careem / Jahez** CSV/XLSX
- **Zomato** CSV
- **Generic** CSV / XLSX / JSON with any rating + text columns
- **A folder** of any of the above (merged automatically)

See [`references/input-formats.md`](references/input-formats.md) for column auto-detection rules.

## Themes detected

Food quality · Service & Staff · Wait Time · Ambiance · Value · Cleanliness · **Halal** · **Family/Singles Section** · **Prayer Area** · **Ramadan/Iftar/Suhoor** · **Shisha** · **Dress Code** · **Smoking Section** · **Delivery (Talabat/HungerStation)** · Menu Variety · Kids Experience · Parking

Bolded themes are GCC-specific. See [`references/gcc-restaurant-lexicon.md`](references/gcc-restaurant-lexicon.md) for the bilingual cue lists.

## Metrics

- **NPS** (Net Promoter Score) — 5★ → P/P/D mapping or 0–10 scale
- **CSAT** — top-2-box satisfaction
- **CES** — friction-keyword proxy (true CES requires a survey)
- **Sentiment** — rating + bilingual lexicon
- **Per-theme sentiment split** — one review can be positive on food, negative on wait time

See [`references/metrics-guide.md`](references/metrics-guide.md) for benchmarks and caveats.

---

## Privacy

Everything runs locally. No data leaves your machine. The only network call is the **first-time** Chart.js download (cached in `assets/chart.umd.min.js`); after that, the entire toolchain is offline.

Reviews often contain reviewer names, emails, or phone numbers in free text. Before sharing the report, search `out/normalized.csv` for `@` or digit patterns and redact as needed.

---

## File map

```
restaurant-feedback-gcc/
├── SKILL.md                 # Skill instructions
├── README.md                # This file
├── LICENSE                  # MIT
├── requirements.txt
├── scripts/
│   ├── analyze.py           # CLI entry: parse → enrich → metrics → JSON
│   ├── parsers.py           # CSV / XLSX / JSON / Google Takeout
│   ├── metrics.py           # NPS / CSAT / CES / sentiment / trend / branch
│   ├── themes.py            # GCC bilingual theme tagger
│   └── build_report.py      # Renders self-contained report.html
├── templates/
│   └── report.html          # HTML template with placeholders
├── references/
│   ├── gcc-restaurant-lexicon.md
│   ├── input-formats.md
│   └── metrics-guide.md
├── examples/
│   ├── sample-reviews.csv
│   ├── sample-narrative.json
│   ├── sample-google-reviews.json
│   ├── sample-narrative-google.json
│   └── sample-google-takeout.json
└── assets/
    └── chart.umd.min.js     # Cached on first run
```

---

## Roadmap

- [ ] Headless PDF export (Playwright)
- [ ] Per-theme trend over time
- [ ] Competitor benchmark mode (compare 2+ restaurants)
- [ ] Aspect-based sentiment via LLM API for higher-quality theme tagging
- [ ] Native Arabic interface for the report

PRs welcome.

## License

MIT. See [LICENSE](LICENSE).

## Credits

Lexicon curated from public review data across KSA, UAE, Kuwait, Qatar, Bahrain, and Oman.

Author: **Mahmoud Al Dinnawi**
