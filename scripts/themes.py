"""GCC restaurant theme tagger. Maps free-text reviews to canonical themes.

Lexicon is intentionally bilingual (EN + AR) and includes common Khaleeji
spellings/dialect (e.g. "خرافي", "زفت", "تحفه").

Each theme has positive and negative cue sets so we can split sentiment
*per theme* rather than per review.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable


# A theme = canonical key, English label, and bilingual cue lists.
# Use \b word boundaries for English; for Arabic we use simple substring match
# because Arabic lacks reliable token boundaries with diacritics/affixes.

THEMES = {
    "food_quality": {
        "label": "Food Quality",
        "en_pos": ["delicious", "tasty", "fresh", "flavorful", "amazing food", "best food", "perfectly cooked"],
        "en_neg": ["bland", "tasteless", "stale", "burnt", "burned", "raw", "soggy", "salty", "undercooked", "overcooked", "cold food"],
        "ar_pos": ["لذيذ", "طعمه", "طازج", "نكهه", "نكهة", "طعام رائع", "اكل ممتاز", "أكل ممتاز", "اكل لذيذ", "أكل لذيذ"],
        "ar_neg": ["تافه", "بدون طعم", "محروق", "نيء", "نيئ", "مالح", "بارد", "مقرف", "زفت", "خايس"],
    },
    "service": {
        "label": "Service & Staff",
        "en_pos": ["friendly staff", "great service", "attentive", "polite", "welcoming", "helpful staff", "amazing service"],
        "en_neg": ["rude", "slow service", "ignored", "unprofessional", "bad service", "staff was rude"],
        "ar_pos": ["خدمه ممتازه", "خدمة ممتازة", "موظف لطيف", "موظفين لطاف", "ترحيب", "راقي"],
        "ar_neg": ["سيء", "وقح", "بطيء", "تجاهل", "غير مهذب", "خدمه سيئه", "خدمة سيئة"],
    },
    "wait_time": {
        "label": "Wait Time",
        "en_pos": ["fast service", "quick service", "no wait", "served quickly", "prompt"],
        "en_neg": ["waited", "long wait", "slow", "delay", "delayed", "took forever", "queue"],
        "ar_pos": ["سريع", "بسرعه", "بدون انتظار"],
        "ar_neg": ["انتظر", "انتظار طويل", "بطيء", "تأخر", "تاخر", "تأخير", "تاخير", "طابور"],
    },
    "ambiance": {
        "label": "Ambiance & Decor",
        "en_pos": ["cozy", "beautiful", "nice atmosphere", "great vibe", "decor", "stylish", "view", "rooftop"],
        "en_neg": ["loud", "noisy", "cramped", "dark", "dated", "boring decor"],
        "ar_pos": ["جلسه حلوه", "جلسة حلوة", "اجواء", "أجواء", "ديكور", "اطلاله", "إطلالة", "هاديء"],
        "ar_neg": ["مزعج", "ضوضاء", "مزدحم", "ضيق"],
    },
    "value": {
        "label": "Value for Money",
        "en_pos": ["worth it", "good value", "reasonable price", "affordable", "great prices"],
        "en_neg": ["overpriced", "expensive", "not worth", "ripoff", "ripped off", "too pricey"],
        "ar_pos": ["سعر مناسب", "اسعار حلوه", "أسعار حلوة", "يستاهل", "تستاهل"],
        "ar_neg": ["غالي", "ما يستاهل", "ما تستاهل", "مكلف", "اسعار مرتفعه", "أسعار مرتفعة"],
    },
    "cleanliness": {
        "label": "Cleanliness",
        "en_pos": ["clean", "spotless", "hygienic", "well maintained"],
        "en_neg": ["dirty", "filthy", "unclean", "hair in", "fly in", "cockroach", "smelled bad", "dirty bathroom"],
        "ar_pos": ["نظيف", "نظافه", "نظافة"],
        "ar_neg": ["وسخ", "غير نظيف", "صرصور", "ذبابه", "ذبابة", "ريحه", "ريحة", "حمام وسخ"],
    },
    "halal": {
        "label": "Halal",
        "en_pos": ["halal certified", "halal", "100% halal", "halal meat"],
        "en_neg": ["not halal", "non-halal", "haram", "alcohol served", "pork"],
        "ar_pos": ["حلال", "ذبيحه شرعيه", "ذبيحة شرعية"],
        "ar_neg": ["غير حلال", "حرام", "خمر", "كحول"],
    },
    "family_section": {
        "label": "Family / Singles Section",
        "en_pos": ["family section", "family friendly", "family area", "kids menu", "kid friendly"],
        "en_neg": ["no family section", "singles only", "no kids", "not family friendly"],
        "ar_pos": ["قسم العائلات", "قسم عائلات", "قسم العوائل", "للعوائل", "مناسب للعوائل", "العائله", "العائلة"],
        "ar_neg": ["ما فيه قسم عائلات", "ما يناسب العوائل", "بدون قسم عائلات"],
    },
    "prayer_area": {
        "label": "Prayer Area / Musalla",
        "en_pos": ["prayer area", "prayer room", "musalla", "place to pray"],
        "en_neg": ["no prayer area", "no musalla", "nowhere to pray"],
        "ar_pos": ["مصلى", "مصلي", "مكان للصلاه", "مكان للصلاة"],
        "ar_neg": ["ما فيه مصلى", "بدون مصلى"],
    },
    "ramadan": {
        "label": "Ramadan / Iftar / Suhoor",
        "en_pos": ["iftar buffet", "great iftar", "suhoor", "ramadan tent", "ramadan menu"],
        "en_neg": ["bad iftar", "iftar was disappointing", "no suhoor", "ran out of food at iftar"],
        "ar_pos": ["افطار", "إفطار", "سحور", "خيمه رمضانيه", "خيمة رمضانية", "بوفيه افطار", "بوفيه إفطار"],
        "ar_neg": ["افطار سيء", "إفطار سيئ", "خلص الاكل", "خلص الأكل"],
    },
    "shisha": {
        "label": "Shisha",
        "en_pos": ["great shisha", "good hookah", "shisha quality", "shisha was perfect"],
        "en_neg": ["bad shisha", "weak shisha", "shisha smell", "smoky shisha", "no shisha"],
        "ar_pos": ["شيشه ممتازه", "شيشة ممتازة", "معسل حلو", "معسّل"],
        "ar_neg": ["شيشه سيئه", "شيشة سيئة", "معسل حارق", "ريحه شيشه", "ريحة شيشة"],
    },
    "dress_code": {
        "label": "Dress Code / Modesty",
        "en_pos": ["respectful dress code", "modest", "appropriate"],
        "en_neg": ["dress code too strict", "abaya issue", "told to cover", "inappropriate dress"],
        "ar_pos": ["محتشم", "لباس محترم"],
        "ar_neg": ["لبس غير محتشم", "متشدد باللبس"],
    },
    "smoking": {
        "label": "Smoking Section",
        "en_pos": ["smoking section", "outdoor smoking", "well ventilated"],
        "en_neg": ["smoke smell", "smoky", "no non-smoking", "cigarette smoke"],
        "ar_pos": ["قسم تدخين", "تهويه ممتازه", "تهوية ممتازة"],
        "ar_neg": ["دخان", "ريحه دخان", "ريحة دخان"],
    },
    "delivery": {
        "label": "Delivery (Talabat / HungerStation / Careem)",
        "en_pos": ["delivered fast", "hot when arrived", "great delivery", "well packaged"],
        "en_neg": ["cold on arrival", "missing items", "wrong order", "spilled", "late delivery", "talabat", "hungerstation"],
        "ar_pos": ["توصيل سريع", "وصل ساخن"],
        "ar_neg": ["ناقص", "طلب غلط", "وصل بارد", "تأخر التوصيل", "تاخر التوصيل", "ناقص الطلب"],
    },
    "menu_variety": {
        "label": "Menu Variety",
        "en_pos": ["great menu", "variety", "lots of options", "good selection"],
        "en_neg": ["limited menu", "no options", "small menu", "menu is boring"],
        "ar_pos": ["قائمه متنوعه", "قائمة متنوعة", "خيارات كثيره", "خيارات كثيرة"],
        "ar_neg": ["قائمه محدوده", "قائمة محدودة", "خيارات قليله", "خيارات قليلة"],
    },
    "kids": {
        "label": "Kids Experience",
        "en_pos": ["kids menu", "play area", "kid friendly", "high chairs"],
        "en_neg": ["no kids menu", "no play area", "not for kids"],
        "ar_pos": ["منيو اطفال", "قائمه اطفال", "قائمة أطفال", "العاب اطفال", "ألعاب أطفال"],
        "ar_neg": ["ما فيه شي للاطفال", "ما فيه شي للأطفال"],
    },
    "parking": {
        "label": "Parking",
        "en_pos": ["valet parking", "easy parking", "parking available", "ample parking"],
        "en_neg": ["no parking", "hard to park", "parking is a nightmare"],
        "ar_pos": ["مواقف متوفره", "مواقف متوفرة", "فاليه"],
        "ar_neg": ["ما فيه مواقف", "مافي مواقف", "صعب توقف"],
    },
}


def _matches(text: str, cues: list[str], en: bool) -> int:
    if not text:
        return 0
    t = text.lower() if en else text
    n = 0
    for cue in cues:
        if en:
            if re.search(rf"\b{re.escape(cue)}\b", t):
                n += 1
        else:
            if cue in t:
                n += 1
    return n


def tag_record(record: dict) -> dict:
    """Returns a new record with `themes` (list of {key, label, sentiment})."""
    text = record.get("text", "") or ""
    found = []
    for key, theme in THEMES.items():
        pos = _matches(text, theme["en_pos"], en=True) + _matches(text, theme["ar_pos"], en=False)
        neg = _matches(text, theme["en_neg"], en=True) + _matches(text, theme["ar_neg"], en=False)
        if pos == 0 and neg == 0:
            continue
        if pos > neg:
            sent = "positive"
        elif neg > pos:
            sent = "negative"
        else:
            sent = "mixed"
        found.append({"key": key, "label": theme["label"], "sentiment": sent})
    return {**record, "themes": found}


def aggregate_themes(records: list[dict], max_quotes: int = 3) -> list[dict]:
    """Counts per theme + sentiment split + sample quotes (positive + negative)."""
    counters: dict[str, dict] = {
        k: {"key": k, "label": v["label"], "positive": 0, "negative": 0, "mixed": 0,
            "pos_quotes": [], "neg_quotes": []}
        for k, v in THEMES.items()
    }
    for r in records:
        for t in r.get("themes", []):
            c = counters[t["key"]]
            c[t["sentiment"]] += 1
            text = (r.get("text") or "").strip()
            if not text:
                continue
            short = text if len(text) <= 280 else text[:277] + "…"
            if t["sentiment"] == "positive" and len(c["pos_quotes"]) < max_quotes:
                c["pos_quotes"].append({"text": short, "rating": r.get("rating"), "lang": r.get("language", "unknown")})
            elif t["sentiment"] == "negative" and len(c["neg_quotes"]) < max_quotes:
                c["neg_quotes"].append({"text": short, "rating": r.get("rating"), "lang": r.get("language", "unknown")})

    out = []
    for c in counters.values():
        total = c["positive"] + c["negative"] + c["mixed"]
        if total == 0:
            continue
        c["total"] = total
        c["positive_pct"] = round(100 * c["positive"] / total, 1)
        c["negative_pct"] = round(100 * c["negative"] / total, 1)
        out.append(c)
    out.sort(key=lambda x: -x["total"])
    return out
