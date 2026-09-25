#!/usr/bin/env python3
"""
Listing checker -- validates a listing JSON against Etsy's field rules
and current listing guidance (Seller Handbook + 2026 optimization guides).

Usage: python3 check_listing.py listings/<name>.json

Rules enforced (source: Etsy Seller Handbook; Listadum/CraftPilot 2026):
  FAIL  title over 140 characters
  FAIL  fewer than 13 tags
  FAIL  any tag over 20 characters
  FAIL  duplicate tag phrases
  WARN  title over ~15 words (Etsy: "consider less than 15 words")
  WARN  "candle" (item noun) not within first 5 title words
  WARN  gifting/aspirational words in title (belongs in tags/description)
  WARN  subjective words ("perfect", "beautiful") in title
  WARN  single-word tag
  WARN  one root word used in 4+ tags (diversify angles instead)
  WARN  primary keyword missing from first 160 chars of description
  WARN  missing labeled section (SCENT / VESSEL / WAX & WICK / BURN / CARE)
"""

import json
import sys
from collections import Counter

SECTIONS = ["SCENT", "VESSEL", "WAX", "BURN", "CARE"]
SUBJECTIVE = ("perfect", "beautiful", "wonderful", "amazing", "gorgeous")
GIFTING = ("gift for", "birthday present", "gift idea")


def check(path):
    with open(path) as f:
        d = json.load(f)

    fails, warns = [], []
    title = d["title"]
    tags = d["tags"]
    desc = d["description"]
    words = title.replace(",", " ").split()

    if len(title) > 140:
        fails.append(f"title is {len(title)} chars (max 140)")
    if len(words) > 15:
        warns.append(f"title is {len(words)} words (Etsy suggests ~15 or fewer)")
    if "candle" not in [w.lower() for w in words[:5]]:
        warns.append("item noun 'candle' not in first 5 title words")
    tl = title.lower()
    for w in SUBJECTIVE:
        if w in tl:
            warns.append(f"subjective word '{w}' in title (move to description)")
    for g in GIFTING:
        if g in tl:
            warns.append(f"gifting phrase '{g}' in title (Etsy: keep in tags)")

    if len(tags) < 13:
        fails.append(f"only {len(tags)} tags (use all 13)")
    seen = set()
    for t in tags:
        if len(t) > 20:
            fails.append(f"tag '{t}' is {len(t)} chars (max 20)")
        if " " not in t:
            warns.append(f"tag '{t}' is single-word (use phrases)")
        if t.lower() in seen:
            fails.append(f"duplicate tag '{t}'")
        seen.add(t.lower())
    roots = Counter()
    for t in tags:
        for w in t.lower().split():
            if w not in ("and", "for", "the"):
                roots[w] += 1
    for root, n in roots.most_common():
        if n >= 4:
            warns.append(f"root '{root}' appears in {n} tags (diversify)")

    first160 = desc[:160].lower()
    if "candle" not in first160:
        warns.append("primary keyword 'candle' not in first 160 chars of description")
    for s in SECTIONS:
        if s not in desc.upper():
            warns.append(f"no labeled '{s}' section in description")

    # render
    print(f"== {d['name']} ({path}) ==")
    if d.get("voice_status"):
        print(f"[voice: {d['voice_status']}]")
    print()
    print(f"TITLE ({len(title)}/140 chars, {len(words)} words):")
    print(f"  {title}")
    print()
    print(f"TAGS ({len(tags)}/13):")
    for t in tags:
        print(f"  [{len(t):>2}] {t}")
    print()
    print("DESCRIPTION:")
    for line in desc.split("\n"):
        print(f"  {line}")
    print()
    print("ATTRIBUTES:")
    for k, v in d.get("attributes", {}).items():
        print(f"  {k}: {v}")
    print()

    print(f"RESULT: {'FAIL' if fails else 'PASS'} "
          f"({len(fails)} fail, {len(warns)} warn)")
    for m in fails:
        print(f"  FAIL: {m}")
    for m in warns:
        print(f"  WARN: {m}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(check(sys.argv[1]))
