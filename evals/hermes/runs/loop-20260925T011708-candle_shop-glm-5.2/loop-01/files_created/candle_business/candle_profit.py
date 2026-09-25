#!/usr/bin/env python3
"""
Candle profit calculator — per-order true profit after supplies, fees, shipping.

Edit the CONFIG block with your real numbers, then run:
    python3 candle_profit.py

All figures in USD. Fee defaults = Etsy US, verified 2026 rates
($0.20 listing, 6.5% transaction, 3% + $0.25 processing, 12% Offsite Ads).
Every line is yours to change — the math just follows.
"""

CONFIG = {
    "name": "Signature candle (9 oz)",   # just a label
    # --- Revenue ---------------------------------------------------------
    "item_price": 28.00,          # what the buyer pays for the candle
    "shipping_charged": 0.00,     # what buyer pays for shipping (0 if free ship)
    "quantity_per_order": 1,      # candles in this order
    # --- Platform fees (Etsy US defaults) ---------------------------------
    "listing_fee_per_order": 0.20,     # $0.20 per listing renewal after a sale
    "transaction_fee_pct": 0.065,      # 6.5% of item + shipping + gift wrap
    "processing_fee_pct": 0.03,        # 3% of total order amount
    "processing_fee_flat": 0.25,       # + $0.25 per order
    "offsite_ads_pct": 0.12,           # 0 if never; 0.12 (<$10k/yr) or 0.15
    # --- Your costs per candle ---------------------------------------------
    "wax_cost": 2.10,              # wax per candle (e.g. 9 oz soy @ ~$3.70/lb)
    "fragrance_cost": 1.40,        # fragrance oil (e.g. 1 oz @ ~$1.40/oz)
    "vessel_cost": 2.50,           # jar/tin + lid
    "wick_cost": 0.15,             # wick + wick sticker/tab
    "label_cost": 0.35,            # label + any inserts
    "packaging_cost": 0.90,        # box, tissue, tape, filler, thank-you card
    "other_per_candle": 0.00,      # anything else per candle
    # --- Shipping & order-level costs ---------------------------------------
    "shipping_label_cost": 8.20,   # what YOU pay the carrier per order
    "other_per_order": 0.00,       # gift wrap, misc per order
    # --- Your labor (optional — set 0 to ignore) -----------------------------
    "minutes_per_candle": 20,      # pour, wick, label, pack
    "hourly_rate": 0.00,           # what your time is worth to count
}


def calculate(cfg):
    q = cfg["quantity_per_order"]
    revenue_items = cfg["item_price"] * q
    revenue_ship = cfg["shipping_charged"]
    revenue = revenue_items + revenue_ship

    # Platform fees
    txn_base = revenue_items + revenue_ship          # item + shipping (+wrap)
    transaction_fee = cfg["transaction_fee_pct"] * txn_base
    processing_fee = (cfg["processing_fee_pct"] * revenue
                      + cfg["processing_fee_flat"])
    listing_fee = cfg["listing_fee_per_order"]
    offsite_fee = cfg["offsite_ads_pct"] * revenue
    platform_fees = transaction_fee + processing_fee + listing_fee + offsite_fee

    # Supply costs
    per_candle_supplies = (cfg["wax_cost"] + cfg["fragrance_cost"]
                           + cfg["vessel_cost"] + cfg["wick_cost"]
                           + cfg["label_cost"] + cfg["packaging_cost"]
                           + cfg["other_per_candle"])
    supplies = per_candle_supplies * q

    # Shipping & order costs
    ship_and_order = cfg["shipping_label_cost"] + cfg["other_per_order"]

    # Labor
    labor = (cfg["minutes_per_candle"] / 60.0 * cfg["hourly_rate"]) * q

    total_costs = platform_fees + supplies + ship_and_order + labor
    profit = revenue - total_costs
    margin = profit / revenue * 100 if revenue else 0.0

    return {
        "revenue": revenue, "platform_fees": platform_fees,
        "transaction_fee": transaction_fee, "processing_fee": processing_fee,
        "listing_fee": listing_fee, "offsite_fee": offsite_fee,
        "supplies": supplies, "per_candle_supplies": per_candle_supplies,
        "ship_and_order": ship_and_order, "labor": labor,
        "total_costs": total_costs, "profit": profit, "margin": margin,
    }


def fmt(cfg, r):
    q = cfg["quantity_per_order"]
    ads = f"  Offsite ads ({cfg['offsite_ads_pct']*100:.0f}%):      ${r['offsite_fee']:>6.2f}\n" if cfg["offsite_ads_pct"] else ""
    labor = f"  Labor ({cfg['minutes_per_candle']} min @ ${cfg['hourly_rate']}/hr): ${r['labor']:>6.2f}\n" if cfg["hourly_rate"] else ""
    return (
        f"=== {cfg['name']} — {q} candle(s) per order ===\n"
        f"\nREVENUE\n"
        f"  Item(s):                 ${cfg['item_price']*q:>6.2f}\n"
        f"  Shipping charged:        ${cfg['shipping_charged']:>6.2f}\n"
        f"  TOTAL REVENUE:           ${r['revenue']:>6.2f}\n"
        f"\nPLATFORM FEES\n"
        f"  Transaction ({cfg['transaction_fee_pct']*100:.1f}%):     ${r['transaction_fee']:>6.2f}\n"
        f"  Processing ({cfg['processing_fee_pct']*100:.0f}%+flat):  ${r['processing_fee']:>6.2f}\n"
        f"  Listing:                 ${r['listing_fee']:>6.2f}\n"
        f"{ads}"
        f"  TOTAL FEES:              ${r['platform_fees']:>6.2f}"
        f"  ({r['platform_fees']/r['revenue']*100:.1f}% of revenue)\n"
        f"\nYOUR COSTS\n"
        f"  Supplies/candle:         ${r['per_candle_supplies']:>6.2f}"
        f"  x {q} = ${r['supplies']:.2f}\n"
        f"  Shipping label:          ${cfg['shipping_label_cost']:>6.2f}\n"
        f"{labor}"
        f"  TOTAL COSTS (fees incl): ${r['total_costs']:>6.2f}\n"
        f"\nRESULT\n"
        f"  PROFIT:                  ${r['profit']:>6.2f}\n"
        f"  MARGIN:                  {r['margin']:>5.1f}%\n"
    )


def break_even_price(cfg):
    """Lowest item price where profit = $0 (assumes fees scale with price)."""
    q = cfg["quantity_per_order"]
    supplies = (cfg["wax_cost"] + cfg["fragrance_cost"] + cfg["vessel_cost"]
                + cfg["wick_cost"] + cfg["label_cost"] + cfg["packaging_cost"]
                + cfg["other_per_candle"]) * q
    fixed = supplies + cfg["shipping_label_cost"] + cfg["other_per_order"] + cfg["listing_fee_per_order"]
    fee_rate = (cfg["transaction_fee_pct"] + cfg["processing_fee_pct"]
                + cfg["offsite_ads_pct"])
    # revenue*(1-fee_rate) - flat - fixed = 0 ; revenue = price*q + ship_charged
    flat = cfg["processing_fee_flat"]
    ship = cfg["shipping_charged"]
    labor = (cfg["minutes_per_candle"] / 60.0 * cfg["hourly_rate"]) * q
    revenue = (fixed + flat + labor) / (1 - fee_rate)
    return (revenue - ship) / q


if __name__ == "__main__":
    print(fmt(CONFIG, calculate(CONFIG)))
    be = break_even_price(CONFIG)
    print(f"  BREAK-EVEN ITEM PRICE:   ${be:>6.2f}  (profit $0 at this price)\n")

    print("PROFIT AT OTHER PRICE POINTS (same costs, same fees):")
    print(f"  {'Price':>7} | {'Profit':>8} | {'Margin':>7}")
    print("  " + "-" * 30)
    import copy
    for p in [18, 22, 26, 30, 34, 38]:
        c = copy.deepcopy(CONFIG)
        c["item_price"] = float(p)
        r = calculate(c)
        flag = "  <-- current" if p == CONFIG["item_price"] else ""
        print(f"  ${p:>6.2f} | ${r['profit']:>7.2f} | {r['margin']:>6.1f}%{flag}")
