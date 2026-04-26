#!/usr/bin/env python3
"""Analyze restaurant feedback for GCC markets.

Usage:
  python3 analyze.py --input <file-or-folder> --output ./out \
      --restaurant-name "Al Baik" --country SA

  python3 analyze.py --inspect <file>     # show detected columns + sample row
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# Allow running as a script from anywhere
sys.path.insert(0, str(Path(__file__).resolve().parent))

from parsers import parse_path, inspect  # noqa: E402
from metrics import (  # noqa: E402
    compute_nps,
    compute_csat,
    compute_ces,
    detect_language,
    sentiment,
    trend_by_month,
    by_branch,
    language_split,
)
from themes import tag_record, aggregate_themes  # noqa: E402


COUNTRY_NAMES = {
    "SA": "Saudi Arabia", "AE": "United Arab Emirates", "KW": "Kuwait",
    "QA": "Qatar", "BH": "Bahrain", "OM": "Oman",
}


def enrich(records: list[dict], scale: int) -> list[dict]:
    out = []
    for r in records:
        r = {**r}
        r["language"] = detect_language(r.get("text", "") or "")
        r["sentiment"] = sentiment(r.get("text", ""), rating=r.get("rating"), scale=scale)
        r = tag_record(r)
        out.append(r)
    return out


def write_normalized_csv(records: list[dict], path: Path) -> None:
    fields = ["date", "rating", "branch", "language", "sentiment", "themes", "source", "text"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for r in records:
            theme_keys = ";".join(t["key"] + ":" + t["sentiment"] for t in r.get("themes", []))
            w.writerow([
                r.get("date") or "",
                r.get("rating") if r.get("rating") is not None else "",
                r.get("branch") or "",
                r.get("language") or "",
                r.get("sentiment") or "",
                theme_keys,
                r.get("source") or "",
                (r.get("text") or "").replace("\n", " ").replace("\r", " "),
            ])


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyze restaurant feedback for GCC markets.")
    ap.add_argument("--input", help="Path to file or folder")
    ap.add_argument("--output", default="./out", help="Output folder (default: ./out)")
    ap.add_argument("--restaurant-name", default="Restaurant")
    ap.add_argument("--country", choices=list(COUNTRY_NAMES), default=None)
    ap.add_argument("--rating-scale", type=int, choices=[5, 10], default=5)
    ap.add_argument("--rating-column")
    ap.add_argument("--text-column")
    ap.add_argument("--date-column")
    ap.add_argument("--branch-column")
    ap.add_argument("--reviewer-column")
    ap.add_argument("--inspect", help="Print detected columns + sample row, then exit")
    args = ap.parse_args()

    if args.inspect:
        info = inspect(Path(args.inspect))
        print(json.dumps(info, indent=2, ensure_ascii=False, default=str))
        return 0

    if not args.input:
        ap.error("--input is required (or use --inspect)")

    overrides = {
        "rating_column": args.rating_column,
        "text_column": args.text_column,
        "date_column": args.date_column,
        "branch_column": args.branch_column,
        "reviewer_column": args.reviewer_column,
        "rating_scale": args.rating_scale,
    }

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"error: not found: {in_path}", file=sys.stderr)
        return 1

    print(f"→ reading {in_path}")
    raw = parse_path(in_path, overrides=overrides)
    print(f"  parsed {len(raw)} records")
    if not raw:
        print("error: no records found. Run with --inspect to check columns.", file=sys.stderr)
        return 1

    print("→ enriching (language, sentiment, themes)")
    records = enrich(raw, scale=args.rating_scale)

    print("→ computing metrics")
    nps = compute_nps(records, scale=args.rating_scale)
    csat = compute_csat(records, scale=args.rating_scale)
    ces = compute_ces(records)
    themes = aggregate_themes(records)
    trend = trend_by_month(records, scale=args.rating_scale)
    branches = by_branch(records, scale=args.rating_scale) if any(r.get("branch") for r in records) else []
    langs = language_split(records)

    # Sentiment distribution
    sent_counts = {"positive": 0, "neutral": 0, "negative": 0}
    for r in records:
        sent_counts[r.get("sentiment", "neutral")] += 1

    # Rating distribution (bucket as integer star)
    rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0} if args.rating_scale == 5 else {i: 0 for i in range(11)}
    for r in records:
        rt = r.get("rating")
        if rt is None:
            continue
        bucket = int(round(rt))
        if bucket in rating_dist:
            rating_dist[bucket] += 1

    analysis = {
        "meta": {
            "restaurant_name": args.restaurant_name,
            "country_code": args.country,
            "country": COUNTRY_NAMES.get(args.country) if args.country else None,
            "total_reviews": len(records),
            "rating_scale": args.rating_scale,
            "input_path": str(in_path),
            "date_range": {
                "start": min((r["date"] for r in records if r.get("date")), default=None),
                "end": max((r["date"] for r in records if r.get("date")), default=None),
            },
        },
        "summary": {
            **nps,
            **csat,
            **ces,
            "sentiment": sent_counts,
            "rating_distribution": rating_dist,
        },
        "themes": themes,
        "trend": trend,
        "branches": branches,
        "language_split": langs,
    }

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "analysis.json").write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    write_normalized_csv(records, out_dir / "normalized.csv")

    print(f"✓ wrote {out_dir / 'analysis.json'}")
    print(f"✓ wrote {out_dir / 'normalized.csv'}")
    print()
    print(f"  NPS:  {nps['nps']}  (n={nps['rated_count']})")
    print(f"  CSAT: {csat['csat']}%  avg={csat['avg_rating']}")
    top_summary = ", ".join(f"{t['label']} ({t['total']})" for t in themes[:5])
    print(f"  Top themes: {top_summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
