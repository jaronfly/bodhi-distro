#!/usr/bin/env python3
"""Candle shop profit report: estimate mode (default) or actual mode (orders.csv).

Usage:
    python3 profit.py           # estimates from products.csv volumes
    python3 profit.py actual    # real numbers from orders.csv

Plain stdlib only. Reads config.csv, products.csv, orders.csv,
monthly_costs.csv from this script's directory.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def read_csv(name):
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        sys.exit(f"Missing file: {path}")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def money(x):
    return f"${x:,.2f}"


def load_config():
    cfg = {}
    for row in read_csv("config.csv"):
        try:
            cfg[row["key"]] = float(row["value"])
        except ValueError:
            cfg[row["key"]] = row["value"]
    return cfg


def fee_for_order(item_total, shipping_charged, qty, offsite, cfg):
    """Etsy fees (US, verified Sept 2026) for one order."""
    order_total = item_total + shipping_charged
    listing = cfg["listing_fee"] * qty
    transaction = order_total * cfg["transaction_fee_pct"] / 100.0
    processing = order_total * cfg["processing_fee_pct"] / 100.0 + cfg["processing_fee_fixed"]
    ads = order_total * cfg["offsite_ads_pct"] / 100.0 if offsite else 0.0
    return listing, transaction, processing, ads


def load_products():
    products = {}
    for row in read_csv("products.csv"):
        name = row["name"].strip()
        products[name] = {
            "price": float(row["price"]),
            "shipping_charged": float(row["shipping_charged"]),
            "materials": float(row["materials_cost"]),
            "label": float(row["shipping_label_cost"]),
            "packaging": float(row["packaging_cost"]),
            "units": float(row["est_units_per_month"]),
        }
    return products


def estimate_mode():
    cfg = load_config()
    products = load_products()
    share = cfg.get("share_of_orders_with_offsite_ads", 0.0)
    labor_rate = cfg.get("labor_rate_per_hour", 0.0)
    minutes = cfg.get("minutes_per_unit", 0.0)
    labor_per_unit = labor_rate * minutes / 60.0

    print("=" * 64)
    print(f"  ESTIMATE MODE  ({cfg.get('shop_name', 'shop')})")
    print("  Placeholder numbers until you edit products.csv / config.csv")
    print("=" * 64)

    total_month_profit = 0.0
    total_month_revenue = 0.0
    total_month_fees = 0.0
    for name, p in products.items():
        revenue = p["price"] + p["shipping_charged"]
        listing, transaction, processing, _ = fee_for_order(
            p["price"], p["shipping_charged"], 1, False, cfg)
        expected_ads = revenue * cfg["offsite_ads_pct"] / 100.0 * share
        fees = listing + transaction + processing + expected_ads
        cogs = p["materials"] + p["label"] + p["packaging"]
        profit = revenue - fees - cogs - labor_per_unit
        margin = profit / revenue * 100 if revenue else 0.0
        monthly = profit * p["units"]
        total_month_profit += monthly
        total_month_revenue += revenue * p["units"]
        total_month_fees += fees * p["units"]

        print(f"\n{name}  (~{p['units']:.0f}/mo)")
        print(f"  revenue/unit     {money(revenue):>10}   (price {money(p['price'])}"
              f" + ship charged {money(p['shipping_charged'])})")
        print(f"  etsy fees/unit   {money(fees):>10}   ({fees/revenue*100:.1f}% incl."
              f" {share*100:.0f}% odds of {cfg['offsite_ads_pct']:.0f}% offsite-ads)")
        print(f"    listing {money(listing)} / txn {money(transaction)}"
              f" / proc {money(processing)} / exp.ads {money(expected_ads)}")
        print(f"  your costs/unit  {money(cogs):>10}   (materials {money(p['materials'])}"
              f" + label {money(p['label'])} + pkg {money(p['packaging'])}")
        if labor_per_unit:
            print(f"  labor/unit       {money(labor_per_unit):>10}")
        print(f"  PROFIT/unit      {money(profit):>10}   margin {margin:.1f}%")
        print(f"  profit/month     {money(monthly):>10}")

    fixed = (cfg.get("etsy_ads_budget_monthly", 0.0)
             + cfg.get("etsy_plus_monthly", 0.0)
             + cfg.get("other_fixed_monthly", 0.0))
    monthly_rows = read_csv("monthly_costs.csv")
    extra = sum(float(r["amount"]) for r in monthly_rows if r.get("amount"))

    print("\n" + "-" * 64)
    print(f"  Monthly revenue        {money(total_month_revenue):>12}")
    print(f"  - Etsy fees            {money(total_month_fees):>12}")
    print(f"  - supplies & shipping  {money(total_month_revenue - total_month_fees - total_month_profit):>12}")
    if labor_per_unit:
        units_total = sum(p["units"] for p in products.values())
        print(f"  - labor (yours)        {money(labor_per_unit * units_total):>12}")
    print(f"  - fixed (ads/plus/etc) {money(fixed):>12}")
    if extra:
        print(f"  - monthly_costs.csv    {money(extra):>12}")
    net = total_month_profit - fixed - extra
    print(f"  NET PROFIT/month       {money(net):>12}"
          f"   ({net/total_month_revenue*100:.1f}% of revenue)" if total_month_revenue else "")
    if net < 0:
        print("\n  !! At these numbers the shop LOSES money each month.")
        print("     Edit products.csv prices/costs -- these are placeholders, not truth.")


def actual_mode():
    import datetime
    cfg = load_config()
    products = load_products()
    orders = [r for r in read_csv("orders.csv") if r.get("date")]
    if not orders:
        sys.exit("orders.csv is empty -- add real orders or use estimate mode.")

    months = {}
    unknown = set()
    for o in orders:
        name = o["product"].strip()
        if name not in products:
            unknown.add(name)
            continue
        p = products[name]
        qty = int(o["qty"])
        item_total = float(o["item_total"])
        ship = float(o["shipping_charged"] or 0)
        offsite = o.get("offsite_ad", "no").strip().lower() in ("yes", "y", "true", "1")
        listing, transaction, processing, ads = fee_for_order(
            item_total, ship, qty, offsite, cfg)
        fees = listing + transaction + processing + ads
        cogs = (p["materials"] + p["label"] + p["packaging"]) * qty
        revenue = item_total + ship
        profit = revenue - fees - cogs
        m = o["date"][:7]
        d = months.setdefault(m, {"rev": 0.0, "fees": 0.0, "cogs": 0.0,
                                  "profit": 0.0, "orders": 0})
        d["rev"] += revenue
        d["fees"] += fees
        d["cogs"] += cogs
        d["profit"] += profit
        d["orders"] += 1

    if unknown:
        print("WARNING: orders reference products not in products.csv (skipped):")
        for u in sorted(unknown):
            print(f"  - {u}")
        print()

    fixed = (cfg.get("etsy_ads_budget_monthly", 0.0)
             + cfg.get("etsy_plus_monthly", 0.0)
             + cfg.get("other_fixed_monthly", 0.0))
    extras = {}
    for r in read_csv("monthly_costs.csv"):
        if r.get("amount"):
            extras.setdefault(r["month"], 0.0)
            extras[r["month"]] += float(r["amount"])

    print("=" * 64)
    print(f"  ACTUAL MODE  ({cfg.get('shop_name', 'shop')})  -- from orders.csv")
    print("=" * 64)
    print(f"{'month':<9}{'orders':>7}{'revenue':>12}{'fees':>10}"
          f"{'supplies':>11}{'fixed':>9}{'profit':>11}")
    grand = 0.0
    for m in sorted(months):
        d = months[m]
        fx = fixed + extras.get(m, 0.0)
        net = d["profit"] - fx
        grand += net
        print(f"{m:<9}{d['orders']:>7}{money(d['rev']):>12}{money(d['fees']):>10}"
              f"{money(d['cogs']):>11}{money(fx):>9}{money(net):>11}")
    print("-" * 64)
    print(f"Net profit across all months: {money(grand)}")
    fee_pct = sum(months[m]['fees'] for m in months) / max(
        sum(months[m]['rev'] for m in months), 0.01) * 100
    print(f"Etsy fees as % of revenue: {fee_pct:.1f}%")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "actual":
        actual_mode()
    else:
        estimate_mode()
