# Metrics Guide

What each metric means, how it's computed, and what a "good" number looks like for GCC restaurants.

## NPS — Net Promoter Score

**What it is:** % Promoters − % Detractors. Range: −100 to +100.

**How we compute it from star ratings (5-point scale):**
- Promoter = 5★
- Passive = 4★
- Detractor = 1–3★

This 5★ → NPS mapping is the industry-standard convention used by Trustpilot, Yotpo, and most CX platforms when only star ratings are available. The "true" NPS question (0–10) gives a slightly different distribution — if you have 0–10 survey data, pass `--rating-scale 10` and the parser uses the canonical mapping (9–10 = Promoter, 7–8 = Passive, 0–6 = Detractor).

**GCC restaurant benchmarks** (from public review data, 2023–2025):

| NPS | Reading |
|---|---|
| 50+ | Top decile. Usually only achievable with brand-loyal QSR (e.g. Al Baik, AlRomansiah). |
| 30–49 | Strong. Above GCC F&B median. Probably has a small but loud detractor base. |
| 10–29 | Median. Most casual dining sits here. Service consistency is usually the gap. |
| 0–9 | At risk. Operational issues, not brand issues. |
| < 0 | Detractors outnumber promoters. Investigate immediately. |

**Important caveats:**
1. NPS based on public reviews is **biased toward extremes** — happy and angry customers are over-represented. Internal survey NPS tends to run 10–20 points higher than public-review NPS.
2. **Don't compare across countries blindly.** UAE customers tend to give higher star ratings than Saudi customers for the same experience. KSA reviews are more critical.
3. Anything below n=30 is too small for reliable NPS. The skill warns when this happens.

## CSAT — Customer Satisfaction

**What it is:** % of ratings at the top 2 boxes (4★ or 5★ on a 5-scale; 8–10 on a 10-scale).

**Why we report it alongside NPS:** CSAT captures Passives that NPS treats as neutral. A restaurant with NPS 25 and CSAT 75% is mostly satisfying customers but not creating evangelists. NPS 25 and CSAT 50% means a polarized base.

**GCC benchmarks:** 70%+ is healthy for casual dining. 80%+ for QSR.

## CES — Customer Effort Score (proxy)

True CES requires asking customers "How easy was it to deal with us?" on a 1–7 scale. We don't have that in review data, so we use a **proxy**: the % of reviews that mention friction keywords (waited, long, slow, delayed, refund, complain, طابور, تأخر, شكوى).

**How to use it:** Compare across cohorts (branches, months) — a rising effort signal usually precedes an NPS drop by 1–2 months. Treat the absolute number with skepticism.

## Sentiment

A lightweight heuristic: rating + bilingual lexicon. Not as accurate as a real LLM-based classifier, but consistent and explainable.

- If rating ≥ 4 (or ≥ 8 on 10-scale): positive
- If rating ≤ 2 (or ≤ 5 on 10-scale): negative
- Else: text classification using cue counts; ties → neutral

If you want higher-quality sentiment, post-process `normalized.csv` through an LLM and re-run the report builder.

## Theme sentiment

For each theme, we count cue matches in the positive cue list vs. the negative cue list — **per review**. This means one review can be "positive on food, negative on wait time," which is much more useful than one review-level sentiment.

The theme bar in the report shows the per-theme split, not the overall review split.

## Why these specific metrics?

- **NPS** for board-level reporting and competitor benchmarking
- **CSAT** for week-to-week ops tracking
- **CES proxy** as an early warning indicator
- **Theme sentiment** for prioritizing operational fixes

If your stakeholder wants something else (e.g. **Reichheld's loyalty index**, weighted satisfaction, weighted CSAT by branch revenue) — extend `scripts/metrics.py` and the template. The template uses placeholder substitution, so adding a new KPI card is ~10 lines.
