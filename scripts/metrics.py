"""NPS / CSAT / CES math + sentiment heuristics.

For NPS we accept either:
  - 0-10 scale directly (Promoter 9-10, Passive 7-8, Detractor 0-6)
  - 1-5 star scale → mapped: 5★=Promoter, 4★=Passive, 1-3★=Detractor
"""
from __future__ import annotations

import re
from collections import defaultdict
from statistics import mean
from typing import Iterable


def classify_nps(rating: float, scale: int = 5) -> str | None:
    if rating is None:
        return None
    if scale == 10:
        if rating >= 9:
            return "promoter"
        if rating >= 7:
            return "passive"
        return "detractor"
    # 5-star mapping (industry-standard for restaurant reviews)
    if rating >= 5:
        return "promoter"
    if rating >= 4:
        return "passive"
    return "detractor"


def compute_nps(records: list[dict], scale: int = 5) -> dict:
    counts = {"promoter": 0, "passive": 0, "detractor": 0}
    rated = 0
    for r in records:
        cat = classify_nps(r.get("rating"), scale=scale)
        if cat:
            counts[cat] += 1
            rated += 1
    if rated == 0:
        return {"nps": None, "rated_count": 0, **counts, "promoter_pct": 0, "passive_pct": 0, "detractor_pct": 0}
    promoter_pct = 100 * counts["promoter"] / rated
    passive_pct = 100 * counts["passive"] / rated
    detractor_pct = 100 * counts["detractor"] / rated
    return {
        "nps": round(promoter_pct - detractor_pct, 1),
        "rated_count": rated,
        "promoter_pct": round(promoter_pct, 1),
        "passive_pct": round(passive_pct, 1),
        "detractor_pct": round(detractor_pct, 1),
        **counts,
    }


def compute_csat(records: list[dict], scale: int = 5) -> dict:
    """CSAT = % of ratings at top 2 boxes (4 or 5 on 5-scale, 8-10 on 10-scale)."""
    rated = [r["rating"] for r in records if r.get("rating") is not None]
    if not rated:
        return {"csat": None, "avg_rating": None, "rated_count": 0}
    threshold = 4 if scale == 5 else 8
    satisfied = sum(1 for r in rated if r >= threshold)
    return {
        "csat": round(100 * satisfied / len(rated), 1),
        "avg_rating": round(mean(rated), 2),
        "rated_count": len(rated),
    }


def compute_ces(records: list[dict]) -> dict:
    """CES requires a dedicated 'effort' field, which most public reviews don't have.
    We approximate using complaints about waiting/queue/long/slow/refund.
    Returns inverse signal (higher = MORE effort = bad).
    """
    effort_kw = re.compile(
        r"\b(wait(ed|ing)?|too slow|long queue|line was|delay|delayed|forgot|forgotten|refund|chase|complain|"
        r"انتظر|انتظار|تأخر|تأخير|بطيء|طابور|شكوى)\b",
        re.IGNORECASE,
    )
    flagged = 0
    total = 0
    for r in records:
        if not r.get("text"):
            continue
        total += 1
        if effort_kw.search(r["text"]):
            flagged += 1
    if total == 0:
        return {"ces_effort_pct": None, "sample": 0}
    return {"ces_effort_pct": round(100 * flagged / total, 1), "sample": total}


# --- sentiment (lightweight heuristic) ---------------------------------------

POS_WORDS = {
    # English
    "amazing", "excellent", "great", "love", "loved", "wonderful", "best",
    "delicious", "tasty", "perfect", "friendly", "fast", "quick", "fresh",
    "recommend", "recommended", "awesome", "fantastic", "cozy", "clean",
    # Arabic
    "ممتاز", "رائع", "جميل", "لذيذ", "نظيف", "سريع", "خرافي", "احب", "أحب",
    "افضل", "أفضل", "مميز", "حلو", "تحفه", "تحفة",
}

NEG_WORDS = {
    "bad", "worst", "terrible", "awful", "rude", "slow", "cold", "stale",
    "dirty", "expensive", "overpriced", "disappointed", "disappointing",
    "wait", "waited", "waiting", "ignored", "burnt", "burned", "raw", "soggy",
    "salty", "bland", "horrible", "avoid", "never again",
    "سيء", "سيئ", "بشع", "وسخ", "بطيء", "مالح", "بارد", "محروق", "غالي",
    "خايس", "زفت", "مقرف", "مخيب", "متأخر", "متاخر", "تجاهل",
}


def detect_language(text: str) -> str:
    if not text:
        return "unknown"
    arabic = sum(1 for c in text if "؀" <= c <= "ۿ")
    latin = sum(1 for c in text if c.isalpha() and c.isascii())
    if arabic and latin:
        return "mixed"
    if arabic:
        return "ar"
    if latin:
        return "en"
    return "unknown"


def sentiment(text: str, rating: float | None = None, scale: int = 5) -> str:
    """Combine rating signal with keyword counts. Rating dominates if present."""
    if rating is not None:
        if scale == 5:
            if rating >= 4:
                return "positive"
            if rating <= 2:
                return "negative"
            # 3 → check text
        else:
            if rating >= 8:
                return "positive"
            if rating <= 5:
                return "negative"

    if not text:
        return "neutral"
    t = text.lower()
    pos = sum(1 for w in POS_WORDS if w in t)
    neg = sum(1 for w in NEG_WORDS if w in t)
    if pos > neg + 1:
        return "positive"
    if neg > pos + 1:
        return "negative"
    return "neutral"


# --- aggregators -------------------------------------------------------------

def trend_by_month(records: list[dict], scale: int = 5) -> list[dict]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        d = r.get("date")
        if not d:
            continue
        month = d[:7]  # YYYY-MM
        buckets[month].append(r)
    out = []
    for month in sorted(buckets):
        bucket = buckets[month]
        nps = compute_nps(bucket, scale=scale)
        csat = compute_csat(bucket, scale=scale)
        out.append({
            "month": month,
            "count": len(bucket),
            "nps": nps["nps"],
            "csat": csat["csat"],
            "avg_rating": csat["avg_rating"],
        })
    return out


def by_branch(records: list[dict], scale: int = 5) -> list[dict]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        b = r.get("branch") or "Unknown"
        buckets[b].append(r)
    out = []
    for branch in sorted(buckets, key=lambda x: -len(buckets[x])):
        bucket = buckets[branch]
        nps = compute_nps(bucket, scale=scale)
        csat = compute_csat(bucket, scale=scale)
        out.append({
            "branch": branch,
            "count": len(bucket),
            "nps": nps["nps"],
            "csat": csat["csat"],
            "avg_rating": csat["avg_rating"],
        })
    return out


def language_split(records: list[dict]) -> dict:
    counts = defaultdict(int)
    for r in records:
        counts[r.get("language", "unknown")] += 1
    return dict(counts)
