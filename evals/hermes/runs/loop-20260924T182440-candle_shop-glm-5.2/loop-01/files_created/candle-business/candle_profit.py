#!/usr/bin/env python3
"""
Candle unit-economics calculator.
Computes true per-order profit after supply costs, shipping, and platform fees.

Usage:
  python3 candle_profit.py --demo            # run with example numbers
  python3 candle_profit.py --price 24 --supplies 7.50 ...   # your numbers

All supply costs are per-unit (one candle). Correct them with your real costs;
the defaults are marked ESTIMATE and only exist so the demo runs.
"""
import argparse
import json
import os

# ---------------------------------------------------------------- fee models
# Sources (checked 2026-09): Etsy fees & payments policy summaries;
# Shopify pricing page. US rates — tell me if you sell from another country.

PLATFORMS = {
    "etsy": {
        "listing_fee": 0.20,          # per unit sold (renewal on sale)
        "transaction_pct": 0.065,     # on item price + shipping charged + gift wrap
        "processing_pct": 0.03,       # Etsy Payments, US
        "processing_flat": 0.25,
        "monthly_fixed": 0.0,
        "offsite_ads_pct": 0.15,      # only on ad-attributed sales (12% if >$10k/yr)
    },
    "shopify": {
        "listing_fee": 0.0,
        "transaction_pct": 0.0,
        "processing_pct": 0.029,      # Shopify Payments, Basic plan
        "processing_flat": 0.30,
        "monthly_fixed": 39.0,        # Basic, billed monthly ($29 if annual? no: $39/mo, $29 was legacy)
        "offsite_ads_pct": 0.0,
    },
}


def order_economics(platform, price, ship_charged, supplies, ship_label,
                    packaging=0.0, labor_hours=0.0, labor_rate=0.0,
                    offsite_ad=False, orders_per_month=0):
    """Return dict of per-order economics for one platform."""
    p = PLATFORMS[platform]
    revenue = price + ship_charged

    fees = {}
    fees["listing"] = p["listing_fee"]
    fees["transaction"] = p["transaction_pct"] * revenue
    fees["processing"] = p["processing_pct"] * revenue + p["processing_flat"]
    if offsite_ad and p["offsite_ads_pct"]:
        fees["offsite_ads"] = p["offsite_ads_pct"] * revenue
    total_fees = sum(fees.values())

    costs = {
        "supplies (wax/vessel/wick/fragrance/label)": supplies,
        "packaging": packaging,
        "shipping label": ship_label,
        "labor": labor_hours * labor_rate,
    }
    total_costs = sum(costs.values())

    profit = revenue - total_fees - total_costs
    # Monthly fixed fee amortized over order volume, if given
    amortized_monthly = (p["monthly_fixed"] / orders_per_month) if orders_per_month else 0.0

    return {
        "platform": platform,
        "revenue": revenue,
        "fees": fees,
        "total_fees": total_fees,
        "costs": costs,
        "total_costs": total_costs,
        "profit_per_order": profit,
        "profit_after_monthly_fixed": profit - amortized_monthly,
        "margin_pct": (profit / revenue * 100) if revenue else 0.0,
        "effective_fee_pct": (total_fees / revenue * 100) if revenue else 0.0,
        "amortized_monthly_fee": amortized_monthly,
    }


def price_for_target_margin(platform, target_margin_pct, ship_charged, supplies,
                            ship_label, packaging=0.0, labor_hours=0.0,
                            labor_rate=0.0, offsite_ad=False):
    """Solve numerically for the item price that yields target margin."""
    lo, hi = 0.0, 1000.0
    target = target_margin_pct / 100.0
    for _ in range(100):
        mid = (lo + hi) / 2
        r = order_economics(platform, mid, ship_charged, supplies, ship_label,
                            packaging, labor_hours, labor_rate, offsite_ad)
        if r["margin_pct"] / 100.0 < target:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 2)


def report(r, price, ship_charged):
    lines = []
    add = lines.append
    add(f"  {r['platform'].upper()} — one candle at ${price:.2f} + ${ship_charged:.2f} shipping charged")
    add(f"  Revenue (what buyer pays):        ${r['revenue']:>8.2f}")
    add("")
    add("  Platform fees:")
    for k, v in r["fees"].items():
        add(f"    {k:<34s} ${v:>8.2f}")
    add(f"    {'TOTAL FEES':<34s} ${r['total_fees']:>8.2f}  ({r['effective_fee_pct']:.1f}% of revenue)")
    add("")
    add("  Your costs:")
    for k, v in r["costs"].items():
        add(f"    {k:<34s} ${v:>8.2f}")
    add(f"    {'TOTAL COSTS':<34s} ${r['total_costs']:>8.2f}")
    add("")
    add(f"  PROFIT PER ORDER:                  ${r['profit_per_order']:>8.2f}")
    if r["amortized_monthly_fee"]:
        add(f"  less amortized monthly fee:       -${r['amortized_monthly_fee']:>8.2f}")
        add(f"  PROFIT AFTER SUBSCRIPTION:         ${r['profit_after_monthly_fixed']:>8.2f}")
    add(f"  MARGIN:                             {r['margin_pct']:>7.1f}%")
    return "\n".join(lines)


DEMO = dict(
    price=24.00, ship_charged=0.00, supplies=6.50, ship_label=8.50,
    packaging=1.20, labor_hours=0.25, labor_rate=20.00,
)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--platform", default="both", choices=["etsy", "shopify", "both"])
    ap.add_argument("--price", type=float, help="item price (one candle)")
    ap.add_argument("--ship-charged", type=float, default=0.0, help="shipping buyer pays")
    ap.add_argument("--supplies", type=float, help="wax+vessel+wick+fragrance+label per candle")
    ap.add_argument("--ship-label", type=float, help="what you pay to ship one order")
    ap.add_argument("--packaging", type=float, default=0.0)
    ap.add_argument("--labor-hours", type=float, default=0.0)
    ap.add_argument("--labor-rate", type=float, default=0.0)
    ap.add_argument("--offsite-ad", action="store_true", help="Etsy Offsite Ads attribution")
    ap.add_argument("--orders-per-month", type=float, default=0,
                    help="to amortize Shopify's monthly fee")
    ap.add_argument("--target-margin", type=float, default=None,
                    help="also solve for the price hitting this margin %")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()

    if args.demo:
        print("Running with EXAMPLE numbers (marked ESTIMATE) — replace with yours:\n")
        kw = dict(DEMO)
    else:
        missing = [k for k in ("price", "supplies", "ship_label") if getattr(args, k) is None]
        if missing:
            ap.error(f"missing required args (or use --demo): {missing}")
        kw = dict(price=args.price, ship_charged=args.ship_charged,
                  supplies=args.supplies, ship_label=args.ship_label,
                  packaging=args.packaging, labor_hours=args.labor_hours,
                  labor_rate=args.labor_rate)

    plats = ["etsy", "shopify"] if args.platform == "both" else [args.platform]
    results = {}
    for plat in plats:
        r = order_economics(plat, offsite_ad=args.offsite_ad,
                            orders_per_month=args.orders_per_month, **kw)
        results[plat] = r
        print(report(r, kw["price"], kw["ship_charged"]))
        print()

    if args.target_margin is not None:
        print(f"  Price needed for {args.target_margin:.0f}% margin (same costs):")
        for plat in plats:
            p = price_for_target_margin(plat, args.target_margin,
                                        kw["ship_charged"], kw["supplies"],
                                        kw["ship_label"], kw["packaging"],
                                        kw["labor_hours"], kw["labor_rate"],
                                        args.offsite_ad)
            print(f"    {plat.upper():<8s} ${p:.2f}")
        print()

    if args.offsite_ad and "etsy" in results:
        base = order_economics("etsy", **kw)
        delta = base["profit_per_order"] - results["etsy"]["profit_per_order"]
        print(f"  NOTE: Offsite Ads costs you ${delta:.2f} on this order.")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "last_run.json")
    with open(out, "w") as f:
        json.dump({"inputs": kw, "results": results}, f, indent=2)
    print(f"  (saved to {out})")


if __name__ == "__main__":
    main()
