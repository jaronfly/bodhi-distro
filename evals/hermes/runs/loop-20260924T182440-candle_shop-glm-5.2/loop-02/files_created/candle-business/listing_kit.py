#!/usr/bin/env python3
"""
listing_kit.py -- validate + assemble an Etsy listing from a product sheet JSON.

Division of labor: YOU (or Bodhi, from your interview) write the voice lines
(hook, story) and curate the tag candidates. The script enforces Etsy's actual
mechanical rules and assembles the final listing text.

Rules enforced (verified Sept 2026):
  - title <= 140 chars
  - <= 13 tags, each <= 20 chars, unique, letters/digits/hyphen/apostrophe/space
    (accents allowed; we flag anything else)
  - tags are matched by Etsy as whole phrases -> multi-word tags preferred

Usage: python3 listing_kit.py product_sheet.json
"""
import json, re, sys

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def check_tag(t):
    """Return list of rule violations for one tag."""
    errs = []
    if len(t) > 20:
        errs.append("len=%d>20" % len(t))
    if not re.fullmatch(r"[A-Za-z0-9\-' ]+", t):
        errs.append("bad chars")
    if not t.strip():
        errs.append("empty")
    return errs

def build_title(s):
    parts = [s.get("title_lead") or s["name"]]
    for extra in s.get("title_extras", []):
        parts.append(extra)
    return " | ".join(parts)

def build_tags(s):
    seen, tags, rejected = set(), [], []
    for t in s.get("tag_candidates", []):
        t = t.strip()
        errs = check_tag(t)
        key = t.lower()
        if errs:
            rejected.append((t, ", ".join(errs)))
        elif key in seen:
            rejected.append((t, "duplicate"))
        else:
            seen.add(key)
            tags.append(t)
    return tags, rejected

def build_description(s):
    d = []
    d.append("\n".join(s["hook"]))                       # voice: the scent, her words
    d.append("")
    d.append("THE DETAILS")
    for line in s["details"]:
        d.append("  " + line)
    d.append("")
    d.append(s["story"])                                 # voice: why this candle exists
    d.append("")
    if s.get("care"):
        d.append("BURNING & CARE")
        for line in s["care"]:
            d.append("  " + line)
        d.append("")
    d.append(s.get("footer", "Hand-poured in small batches. Thank you for supporting a small shop."))
    return "\n".join(d)

def main():
    s = load(sys.argv[1])
    title = build_title(s)
    tags, rejected = build_tags(s)
    desc = build_description(s)

    print("=" * 70)
    print("LISTING DRAFT: %s" % s["name"])
    print("=" * 70)
    print()
    print("TITLE (%d/140 chars)%s" % (len(title), "  [TOO LONG]" if len(title) > 140 else ""))
    print(title)
    print()
    print("TAGS (%d/13)" % len(tags))
    for i, t in enumerate(tags, 1):
        print("  %2d. %-22s (%d)" % (i, t, len(t)))
    if rejected:
        print("  rejected (fix or drop):")
        for t, why in rejected:
            print("      %-24s %s" % (t, why))
    if len(tags) < 13:
        print("  [NOTE] %d empty slot(s) -- every empty tag is a search you can't appear in" % (13 - len(tags)))
    print()
    print("DESCRIPTION (%d chars; first 160 shown to Google)" % len(desc))
    print("-" * 70)
    print(desc)
    print("-" * 70)
    print()
    missing = [k for k in ("hook", "story", "details") if not s.get(k)]
    if s.get("voice_is_placeholder"):
        print("[NOTE] hook/story are PLACEHOLDER voice -- replace from INTERVIEW.md answers.")
    if missing:
        print("[WARN] empty required field(s): %s" % ", ".join(missing))
    ok = (len(title) <= 140) and not rejected and len(tags) <= 13 and not missing
    print("CHECKS: %s" % ("ALL PASS" if ok else "SEE NOTES ABOVE"))

if __name__ == "__main__":
    main()
