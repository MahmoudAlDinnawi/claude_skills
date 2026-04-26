# GCC Restaurant Feedback Lexicon

This document explains the bilingual (English + Arabic) keyword sets used by `scripts/themes.py` to tag review themes. Keep it in sync with the THEMES dict in that file.

## Why this matters

Western review-mining tools miss most GCC-specific signals because their lexicons don't include:
- Khaleeji dialect spellings (`خرافي`, `زفت`, `تحفه`, `مايستاهل`)
- Religion/culture themes (halal, prayer area, Ramadan, dress code)
- Family-section vs singles-section distinction (especially KSA)
- Local delivery platforms (Talabat, HungerStation, Careem, Jahez)

If you analyze a GCC restaurant with a generic English-only sentiment tool, you will undercount the Arabic-speaking customer base — typically 40–70% of organic reviews depending on the brand and city.

## Themes covered

| Key | Label | Notes |
|---|---|---|
| `food_quality` | Food Quality | Most universal theme. Burnt / مالح / cold are top complaints. |
| `service` | Service & Staff | Look for `wahed` / `وقح` / `tajahul` تجاهل (ignored). |
| `wait_time` | Wait Time | Often spikes around prayer times in KSA. |
| `ambiance` | Ambiance & Decor | Rooftop / view (`اطلاله`) heavily used in UAE/Bahrain. |
| `value` | Value for Money | `يستاهل` / `ما يستاهل` is a high-signal Khaleeji phrase. |
| `cleanliness` | Cleanliness | Bathroom complaints disproportionately predict churn. |
| `halal` | Halal | Mostly positive (confirms certification), occasional concerns. |
| `family_section` | Family / Singles | KSA-specific historically; still relevant despite 2019 reform. |
| `prayer_area` | Prayer Area / Musalla | Mall-based restaurants get praised when they have one. |
| `ramadan` | Ramadan / Iftar / Suhoor | Volume spikes 3–5× during Ramadan. Treat as separate cohort. |
| `shisha` | Shisha | Highest variance theme — strong love or strong hate. |
| `dress_code` | Dress Code / Modesty | Both directions: too strict OR not respectful enough. |
| `smoking` | Smoking Section | UAE/Bahrain hotels mostly. Smell complaints dominate. |
| `delivery` | Delivery | Always tag separately from dine-in — different ops. |
| `menu_variety` | Menu Variety | Limited menus drive negative passives. |
| `kids` | Kids Experience | Play area, kids menu, high chairs. Family decision driver. |
| `parking` | Parking | Riyadh/Jeddah/Doha mall venues — often deal-breaker. |

## Adding new themes

1. Open `scripts/themes.py`
2. Add a new entry to the `THEMES` dict with `label`, `en_pos`, `en_neg`, `ar_pos`, `ar_neg`
3. Use **substring match** for Arabic (no `\b` boundaries — Arabic morphology breaks them)
4. Use **word boundaries** for English to avoid false positives
5. Add the theme key + label to the table above

## Tips for tuning

- **False positive on a theme?** Move the cue to the opposing sentiment list, or remove if too generic.
- **Missing dialect spelling?** Add common variants — Arabic reviews often have inconsistent diacritics and ta marbuta vs ha (ه vs ة).
- **Brand-specific terms** (signature dishes, branch nicknames): add a brand-themes file and `--themes-extra` flag if needed (not yet implemented).

## Country-specific weighting

Not currently applied automatically, but useful when interpreting:

| Theme | KSA | UAE | KW | QA | BH | OM |
|---|---|---|---|---|---|---|
| family_section | ★★★ | ★ | ★★ | ★★ | ★ | ★★ |
| prayer_area | ★★★ | ★★ | ★★ | ★★★ | ★★ | ★★★ |
| shisha | ★ | ★★★ | ★★ | ★★★ | ★★★ | ★★ |
| dress_code | ★★ | ★ | ★ | ★★ | ★ | ★★ |
| delivery | ★★ | ★★★ | ★★★ | ★★ | ★★ | ★★ |

★★★ = consistently in top 5 mentioned themes. Use this when writing the GCC callouts section.
