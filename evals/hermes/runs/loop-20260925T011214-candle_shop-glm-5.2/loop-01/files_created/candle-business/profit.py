#!/usr/bin/env python3
"""
Candle unit-economics calculator.

Answers: after supplies, shipping, and platform fees, what do I actually
keep on each candle sold?

Edit the CONFIG section below with your real numbers and run:
    python3 profit.py

Fee presets are defaults for typical US sellers -- verify current rates
on your platform's fee schedule, they change.
"""

# ----------------------------------------------------------------------
# CONFIG -- edit these to match your business
# ----------------------------------------------------------------------

PRODUCT = {
    "name": "8oz soy candle (EXAMPLE -- replace with your numbers)",
    "price": 24.00,          # what the customer pays for the candle
    "shipping_charged": 8.00,  # what the customer pays you for shipping
    # supply costs per candle (your materials, not your labor)
    "wax": 2.80,
    "vessel_jar": 2.50,
    "wick": 0.35,
    "fragrance_oil": 1.90,
    "label": 0.40,
    "packaging_box": 1.20,
    "misc": 0.10,            # thank-you card, tape, etc.
    "actual_shipping_cost": 7.50,  # what the carrier charges you
}

# Which platform: "etsy", "shopify", or "custom"
PLATFORM = "etsy"

# Etsy Offsite Ads: 15% if you sell under $10k/yr (optional),
# 12% if over (mandatory). Set True/False.
OFFSITE_ADS = False

# For "custom" platform: fill these in
CUSTOM_FEES = {
    "listing_fee": 0.00,          # per sale
    "transaction_pct": 0.000,     # e.g. 0.065 for 6.5%
    "processing_pct": 0.000,      # e.g. 0.03 for 3%
    "processing_flat": 0.00,      # e.g. 0.25
}

# Shopify has no per-listing fee; monthly plan price is shown separately
# so you can amortize it yourself (plan / units per month).
SHOPIFY_PLAN_MONTHLY = 39.00


# ----------------------------------------------------------------------
# Fee presets (US typical -- verify current rates!)
# ----------------------------------------------------------------------
PRESETS = {
    "etsy": {
        "listing_fee": 0.20,
        "transaction_pct": 0.065,   # 6.5% of price + shipping
        "processing_pct": 0.03,     # 3% of total
        "processing_flat": 0.25,
    },
    "shopify": {
        "listing_fee": 0.00,
        "transaction_pct": 0.000,
        "processing_pct": 0.029,    # Basic plan online card rate
        "processing_flat": 0.30,
    },
    "custom": CUSTOM_FEES,
}


def unit_economics(p, fees, offsite_ads_rate=0.0):
    revenue = p["price"] + p["shipping_charged"]
    supplies = sum(
        p[k] for k in
        ("wax", "vessel_jar", "wick", "fragrance_oil",
         "label", "packaging_box", "misc")
    )
    order_total = p["price"] + p["shipping_charged"]
    listing = fees["listing_fee"]
    transaction = fees["transaction_pct"] * order_total
    processing = fees["processing_pct"] * order_total + fees["processing_flat"]
    offsite = offsite_ads_rate * order_total if offsite_ads_rate else 0.0
    total_fees = listing + transaction + processing + offsite
    shipping_delta = p["actual_shipping_cost"] - p["shipping_charged"]
    net = revenue - supplies - total_fees - p["actual_shipping_cost"]
    return {
        "revenue": revenue,
        "supplies": supplies,
        "listing": listing,
        "transaction": transaction,
        "processing": processing,
        "offsite": offsite,
        "total_fees": total_fees,
        "shipping_gap": shipping_delta,  # >0 means you subsidize shipping
        "net_profit": net,
        "margin_pct": 100.0 * net / revenue,
        "margin_on_price_pct": 100.0 * net / p["price"],
    }


def breakeven_price(p, fees, offsite_ads_rate=0.0, target_margin=0.0):
    """Price needed on the candle itself to keep `target_margin` of
    total revenue as profit, holding shipping fixed."""
    def net_at(price):
        q = dict(p)
        q["price"] = price
        return unit_economics(q, fees, offsite_ads_rate)["net_profit"]
    lo, hi = 0.01, 10_000.0
    target_rev_mult = 1.0 - target_margin  # rough; iterate on net instead
    # bisection on: net_profit == target_margin * revenue
    def f(price):
        q = dict(p)
        q["price"] = price
        r = unit_economics(q, fees, offsite_ads_rate)
        return r["net_profit"] - target_margin * r["revenue"]
    if f(lo) > 0:
        return lo
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def money(x):
    return f"${x:,.2f}"


def report(p, platform, offsite=False):
    fees = PRESETS[platform]
    ads_rate = 0.0
    if platform == "etsy" and offsite:
        ads_rate = 0.15
    r = unit_economics(p, fees, ads_rate)
    print(f"== {p['name']} on {platform.upper()} ==")
    print(f"  Customer pays:            {money(r['revenue']):>10}  "
          f"(candle {money(p['price'])} + shipping {money(p['shipping_charged'])})")
    print(f"  Supplies (COGS):         -{money(r['supplies']):>9}")
    print(f"  Listing fee:             -{money(r['listing']):>9}")
    print(f"  Transaction fee:         -{money(r['transaction']):>9}")
    print(f"  Payment processing:      -{money(r['processing']):>9}")
    if r["offsite"]:
        print(f"  Offsite ads:             -{money(r['offsite']):>9}")
    print(f"  Actual shipping cost:    -{money(p['actual_shipping_cost']):>9}")
    if abs(r["shipping_gap"]) >= 0.005:
        note = "you subsidize shipping" if r["shipping_gap"] > 0 else "shipping adds profit"
        print(f"    (shipping gap {money(r['shipping_gap'])}: {note})")
    print(f"  TOTAL FEES:               {money(r['total_fees']):>10}  "
          f"({r['total_fees'] / r['revenue'] * 100:.1f}% of revenue)")
    print(f"  ------------------------------------------")
    print(f"  NET PROFIT PER CANDLE:    {money(r['net_profit']):>10}")
    print(f"  Margin: {r['margin_pct']:.1f}% of revenue  "
          f"({r['margin_on_price_pct']:.1f}% of candle price)")
    return r


if __name__ == "__main__":
    report(PRODUCT, PLATFORM, offsite=OFFSITE_ADS)
    print()

    # Same candle on the other major platform, for comparison
    other = "shopify" if PLATFORM == "etsy" else "etsy"
    report(PRODUCT, other)
    if other == "shopify":
        print(f"  (plus Shopify plan {money(SHOPIFY_PLAN_MONTHLY)}/month -- "
              f"divide by units sold/month to add per-unit)")
    print()

    # What price keeps 30% margin?
    fees = PRESETS[PLATFORM]
    ads_rate = 0.15 if (PLATFORM == "etsy" and OFFSITE_ADS) else 0.0
    be = breakeven_price(PRODUCT, fees, ads_rate, target_margin=0.0)
    m30 = breakeven_price(PRODUCT, fees, ads_rate, target_margin=0.30)
    print(f"To simply break even on this candle "
          f"(supplies+fees+shipping covered): price it at {money(be)}")
    print(f"To keep a 30% margin on total revenue: price it at {money(m30)}")
