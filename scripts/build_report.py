#!/usr/bin/env python3
"""Render a self-contained HTML report from analysis.json (+ optional narrative.json).

Chart.js is fetched once and cached in ../assets/chart.umd.min.js so the
output HTML is fully offline-capable.
"""
from __future__ import annotations

import argparse
import hashlib
import html as html_lib
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / "templates" / "report.html"
CHART_JS_PATH = ROOT / "assets" / "chart.umd.min.js"
CHART_JS_URL = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"


def ensure_chart_js() -> str:
    if CHART_JS_PATH.exists() and CHART_JS_PATH.stat().st_size > 50_000:
        return CHART_JS_PATH.read_text(encoding="utf-8")
    try:
        print(f"→ fetching Chart.js from {CHART_JS_URL}")
        with urllib.request.urlopen(CHART_JS_URL, timeout=20) as r:
            data = r.read().decode("utf-8")
        CHART_JS_PATH.parent.mkdir(parents=True, exist_ok=True)
        CHART_JS_PATH.write_text(data, encoding="utf-8")
        return data
    except Exception as e:
        print(f"  warning: could not fetch Chart.js ({e}). Falling back to CDN script tag.", file=sys.stderr)
        return f"// Could not embed Chart.js. Loading from CDN at runtime.\n" \
               f'document.write(\'<script src="{CHART_JS_URL}"></scr\' + \'ipt>\');'


def esc(s) -> str:
    return html_lib.escape("" if s is None else str(s))


# ---------- caveats banner ----------

CAVEAT_ICONS = {"warning": "!", "error": "×", "info": "i"}


def render_caveats(items: list) -> str:
    if not items:
        return ""
    parts = []
    for c in items:
        sev = c.get("severity", "info")
        icon = CAVEAT_ICONS.get(sev, "i")
        parts.append(
            f'<div class="caveat {esc(sev)}">'
            f'<span class="icon">{icon}</span>'
            f'<div>{esc(c.get("message",""))}</div>'
            f'</div>'
        )
    return "\n".join(parts)


# ---------- themes ----------

def quote_block(q: dict, sentiment: str) -> str:
    lang_class = "ar" if q.get("lang") == "ar" else ""
    sent_class = "neg" if sentiment == "negative" else ""
    rating = q.get("rating")
    rating_str = f' · {rating}★' if rating else ""
    return (
        f'<blockquote class="{sent_class} {lang_class}">'
        f'{esc(q["text"])}<small>{rating_str}</small>'
        f'</blockquote>'
    )


def render_themes(themes: list) -> str:
    if not themes:
        return '<div class="empty">No themes detected.</div>'
    parts = []
    for t in themes[:14]:
        total = t["total"] or 1
        pos = t["positive"]; neg = t["negative"]; mix = t["mixed"]
        pos_pct = 100 * pos / total
        neg_pct = 100 * neg / total
        mix_pct = 100 * mix / total
        quotes_html = ""
        for q in t.get("pos_quotes", [])[:1]:
            quotes_html += quote_block(q, "positive")
        for q in t.get("neg_quotes", [])[:2]:
            quotes_html += quote_block(q, "negative")
        parts.append(f'''
        <div class="theme reveal" style="--w-pos:{pos_pct:.1f}%; --w-mix:{mix_pct:.1f}%; --w-neg:{neg_pct:.1f}%;">
          <div class="theme-head">
            <span class="theme-title">{esc(t["label"])}</span>
            <span class="theme-count">{t["total"]} mentions</span>
          </div>
          <div class="theme-bar">
            <div class="pos"></div>
            <div class="mix"></div>
            <div class="neg"></div>
          </div>
          <div class="theme-stats">
            <span class="pos">{t["positive_pct"]}% positive</span>
            <span class="neg">{t["negative_pct"]}% negative</span>
          </div>
          <div class="theme-quotes">{quotes_html}</div>
        </div>''')
    return "\n".join(parts)


# ---------- branches ----------

def render_branches(branches: list) -> tuple[str, str]:
    if not branches or len(branches) < 2:
        return "", "display: none;"
    rows = []
    for b in branches:
        rows.append(
            f'<tr><td>{esc(b["branch"])}</td>'
            f'<td class="num">{b["count"]}</td>'
            f'<td class="num">{b["nps"] if b["nps"] is not None else "–"}</td>'
            f'<td class="num">{b["csat"] if b["csat"] is not None else "–"}%</td>'
            f'<td class="num">{b["avg_rating"] if b["avg_rating"] is not None else "–"}</td></tr>'
        )
    return "\n".join(rows), ""


# ---------- strengths / issues / recs ----------

def render_strengths(items: list) -> str:
    if not items:
        return '<div class="empty">Add a narrative.json to populate this section. See SKILL.md for the schema.</div>'
    parts = []
    for s in items:
        parts.append(
            f'<div class="strength-card">'
            f'<h4>{esc(s.get("title",""))}</h4>'
            f'<p>{esc(s.get("detail",""))}</p>'
            f'</div>'
        )
    return "\n".join(parts)


def render_issues(items: list) -> str:
    if not items:
        return '<div class="empty">Add a narrative.json to populate this section.</div>'
    parts = []
    for i in items:
        quote = i.get("quote", "")
        lang = i.get("quote_lang", "en")
        quote_html = ""
        if quote:
            ar_class = " ar" if lang == "ar" else ""
            quote_html = f'<blockquote class="{ar_class.strip()}">{esc(quote)}</blockquote>'
        parts.append(
            f'<div class="issue-card">'
            f'<h4>{esc(i.get("title",""))}</h4>'
            f'<p>{esc(i.get("detail",""))}</p>'
            f'{quote_html}</div>'
        )
    return "\n".join(parts)


def render_recommendations(items: list) -> str:
    if not items:
        return '<div class="empty">Add a narrative.json to populate this section.</div>'
    parts = []
    for r in items:
        prio = (r.get("priority") or "medium").lower()
        parts.append(
            f'<div class="rec">'
            f'<div class="rec-priority {prio}">{prio}</div>'
            f'<div class="rec-body">'
            f'<h4>{esc(r.get("title",""))}</h4>'
            f'<p>{esc(r.get("detail",""))}</p>'
            f'</div></div>'
        )
    return "\n".join(parts)


# ---------- gcc callouts ----------

def render_gcc_callouts(items: list) -> tuple[str, str]:
    if not items:
        return "", "display: none;"
    parts = []
    for c in items:
        # Pick a single-character glyph based on theme
        theme = (c.get("theme") or "").lower()
        if "ramadan" in theme or "iftar" in theme: glyph = "✦"
        elif "halal" in theme: glyph = "ﷲ"
        elif "family" in theme: glyph = "♛"
        elif "prayer" in theme or "musalla" in theme: glyph = "✺"
        elif "shisha" in theme: glyph = "❋"
        elif "delivery" in theme: glyph = "→"
        else: glyph = "◆"
        parts.append(
            f'<div class="gcc-callout">'
            f'<div class="gcc-callout-icon">{glyph}</div>'
            f'<div>'
            f'<strong>{esc(c.get("theme",""))}</strong>'
            f'<div class="gcc-detail">{esc(c.get("insight",""))}</div>'
            f'</div></div>'
        )
    return "\n".join(parts), ""


# ---------- nps class ----------

def nps_class(nps_value, has_caveat: bool) -> tuple[str, str]:
    if nps_value is None:
        # Either no ratings or sample too small — render neutral.
        return ("unknown", "unknown") if has_caveat else ("warn", "warn")
    if nps_value >= 30: return "good", "good"
    if nps_value >= 0:  return "warn", "warn"
    return "bad", "bad"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis", required=True)
    ap.add_argument("--narrative", default=None)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    analysis = json.loads(Path(args.analysis).read_text(encoding="utf-8"))
    narrative = {}
    if args.narrative and Path(args.narrative).exists():
        narrative = json.loads(Path(args.narrative).read_text(encoding="utf-8"))

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    chart_js = ensure_chart_js()

    meta = analysis["meta"]
    summary = analysis["summary"]
    caveats = analysis.get("caveats", [])

    nps_value = summary.get("nps")
    nps_raw = summary.get("nps_raw")
    has_small_sample = any(c.get("key") == "small_sample" for c in caveats)

    nps_kpi_class, nps_text_class = nps_class(nps_value, has_caveat=(nps_value is None and len(caveats) > 0))

    # Display strings
    if nps_value is not None:
        nps_display = str(nps_value)
        nps_counter = str(nps_value)
        nps_raw_note = ""
    elif has_small_sample and nps_raw is not None:
        nps_display = "—"
        nps_counter = "0"  # don't animate to a real number
        nps_raw_note = f" · indicative {nps_raw}"
    else:
        nps_display = "—"
        nps_counter = "0"
        nps_raw_note = ""

    nps_sub = (
        f'{summary.get("rated_count", 0)} ratings'
        if nps_value is not None else "Sample too small for benchmarking"
    )

    csat_value = summary.get("csat")
    csat_display = str(csat_value) if csat_value is not None else "—"
    csat_counter = str(csat_value) if csat_value is not None else "0"

    avg_rating = summary.get("avg_rating")
    avg_str = f"{avg_rating:.2f}" if avg_rating is not None else "—"
    avg_counter = str(avg_rating) if avg_rating is not None else "0"

    ces_value = summary.get("ces_effort_pct")
    ces_display = str(ces_value) if ces_value is not None else "—"
    ces_counter = str(ces_value) if ces_value is not None else "0"

    date_range = "—"
    dr = meta.get("date_range") or {}
    if dr.get("start") and dr.get("end"):
        date_range = f'{dr["start"]} → {dr["end"]}'

    branches_rows, branches_display = render_branches(analysis.get("branches", []))
    gcc_html, gcc_display = render_gcc_callouts(narrative.get("gcc_callouts", []))

    report_id = hashlib.sha256(
        f"{meta.get('restaurant_name')}{meta.get('total_reviews')}{datetime.now().isoformat()}".encode()
    ).hexdigest()[:12].upper()

    replacements = {
        "{{TITLE}}": esc(meta.get("restaurant_name", "Restaurant")),
        "{{COUNTRY}}": esc(meta.get("country") or "GCC"),
        "{{DATE_RANGE}}": esc(date_range),
        "{{TOTAL_REVIEWS}}": str(meta.get("total_reviews", 0)),
        "{{CAVEATS_HTML}}": render_caveats(caveats),
        "{{NPS_VALUE}}": nps_display,
        "{{NPS_COUNTER}}": nps_counter,
        "{{NPS_CLASS}}": nps_kpi_class,
        "{{NPS_TEXT_CLASS}}": nps_text_class,
        "{{NPS_SUB}}": esc(nps_sub),
        "{{NPS_RAW_NOTE}}": esc(nps_raw_note),
        "{{CSAT_VALUE}}": csat_display,
        "{{CSAT_COUNTER}}": csat_counter,
        "{{AVG_RATING}}": avg_str,
        "{{AVG_COUNTER}}": avg_counter,
        "{{SCALE}}": str(meta.get("rating_scale", 5)),
        "{{RATED_COUNT}}": str(summary.get("rated_count", 0)),
        "{{CES_VALUE}}": ces_display,
        "{{CES_COUNTER}}": ces_counter,
        "{{PROMOTER_PCT}}": str(summary.get("promoter_pct", 0)),
        "{{PASSIVE_PCT}}": str(summary.get("passive_pct", 0)),
        "{{DETRACTOR_PCT}}": str(summary.get("detractor_pct", 0)),
        "{{PROMOTER_N}}": str(summary.get("promoter", 0)),
        "{{PASSIVE_N}}": str(summary.get("passive", 0)),
        "{{DETRACTOR_N}}": str(summary.get("detractor", 0)),
        "{{EXECUTIVE_SUMMARY}}": esc(narrative.get("executive_summary",
            "Run analyze.py and write a narrative.json to populate this section. "
            "See SKILL.md for the schema.")),
        "{{THEMES_HTML}}": render_themes(analysis.get("themes", [])),
        "{{BRANCHES_ROWS}}": branches_rows,
        "{{BRANCHES_DISPLAY}}": branches_display,
        "{{GCC_CALLOUTS_HTML}}": gcc_html,
        "{{GCC_DISPLAY}}": gcc_display,
        "{{STRENGTHS_HTML}}": render_strengths(narrative.get("strengths", [])),
        "{{ISSUES_HTML}}": render_issues(narrative.get("issues", [])),
        "{{RECOMMENDATIONS_HTML}}": render_recommendations(narrative.get("recommendations", [])),
        "{{GENERATED_AT}}": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "{{REPORT_ID}}": report_id,
        "{{CHART_JS}}": chart_js,
        "{{DATA_JSON}}": json.dumps(analysis, ensure_ascii=False),
    }

    out = template
    for k, v in replacements.items():
        out = out.replace(k, v)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out, encoding="utf-8")
    print(f"✓ wrote {out_path}  ({out_path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
