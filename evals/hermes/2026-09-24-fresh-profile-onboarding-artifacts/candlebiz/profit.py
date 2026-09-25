#!/usr/bin/env python3
"""Candle profit calculator - real fee math from your order + cost logs.

Usage:
  python3 profit.py            -> full report from orders.csv + costs.csv
  python3 profit.py scenario <item_total> <shipping_charged> <label_cost> <product> [offsite|no]
                                 e.g. python3 profit.py scenario 28 0 6.40 AMBER-8OZ offsite

Fee model (US, verified 2026-09-24 from Etsy's published fee schedule):
  - Listing renewal: $0.20 per item sold (listing auto-renews after a sale)
  - Transaction fee: 6.5% of (item + shipping charged + gift wrap)
  - Payment processing: 3% + $0.25 of total order amount
  - Offsite Ads: 15% of order total when attributed (12% if >$10k/yr sales; capped $100)
  - Platform 'direct' (own site/market): no platform fees
NOTE: sales tax collected by Etsy is excluded here because it isn't your revenue.
      Regulatory Operating Fee does not apply to US-seller shops.
"""
import csv, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
LISTING_FEE = 0.20
TXN_RATE = 0.065
PROC_RATE, PROC_FLAT = 0.03, 0.25
OFFSITE_RATE = 0.15


def load_costs():
    costs = {}
    with open(BASE / "costs.csv", newline="") as f:
        for row in csv.DictReader(f):
            if not row["product"].strip() or row["product"].startswith("#"):
                continue
            costs[row["product"]] = {
                k: float(row[k] or 0)
                for k in ("wax", "vessel", "wick", "fragrance_oil", "label", "packaging_other")
            }
    return costs


def unit_cost(costs, product):
    if product not in costs:
        return None
    c = costs[product]
    return sum(c.values())


def order_fees(platform, item_total, ship_charged, wrap_charged, other_fees, offsite, qty):
    if platform.lower() == "direct":
        return {"platform_fees": 0.0, "listing": 0.0, "txn": 0.0, "proc": 0.0, "ads": 0.0}
    fee_base = item_total + ship_charged + wrap_charged
    listing = LISTING_FEE * qty
    txn = fee_base * TXN_RATE
    proc = fee_base * PROC_RATE + PROC_FLAT
    ads = fee_base * OFFSITE_RATE if str(offsite).strip().lower() in ("yes", "y", "true") else 0.0
    return {"platform_fees": listing + txn + proc + ads, "listing": listing, "txn": txn, "proc": proc, "ads": ads}


def analyze_order(row, costs):
    qty = int(float(row["qty"] or 1))
    item_total = float(row["item_total"] or 0)
    ship_charged = float(row["shipping_charged"] or 0)
    wrap = float(row["gift_wrap_charged"] or 0)
    label = float(row["shipping_label_cost"] or 0)
    other = float(row["other_fees"] or 0)
    product = row["product"]
    uc = unit_cost(costs, product)
    materials = uc * qty if uc is not None else None
    fees = order_fees(row["platform"], item_total, ship_charged, wrap, other, row.get("offsite_ad"), qty)
    revenue = item_total + ship_charged + wrap
    costs_total = (materials or 0) + label + other + fees["platform_fees"]
    profit = revenue - costs_total
    return {
        "date": row["date"], "platform": row["platform"], "product": product, "qty": qty,
        "revenue": revenue, "fees": fees["platform_fees"], "label": label, "other": other,
        "materials": materials, "profit": profit, "unknown_cost": uc is None,
    }


def main():
    costs = load_costs()

    if len(sys.argv) > 1 and sys.argv[1] == "scenario":
        item_total, ship, label = map(float, sys.argv[2:5])
        product = sys.argv[4 + 1] if False else sys.argv[5]
        offsite = sys.argv[6] if len(sys.argv) > 6 else "no"
        qty = 1
        fees = order_fees("etsy", item_total, ship, 0, 0, offsite, qty)
        uc = unit_cost(costs, product)
        revenue = item_total + ship
        materials = uc if uc is not None else 0.0
        profit = revenue - (materials + label + fees["platform_fees"])
        print(f"SCENARIO  {product}  x{qty} on Etsy")
        print(f"  revenue (item+shipping charged)      ${revenue:8.2f}")
        print(f"  - listing renewal                    ${fees['listing']:8.2f}")
        print(f"  - transaction fee (6.5%)             ${fees['txn']:8.2f}")
        print(f"  - payment processing (3%+$0.25)      ${fees['proc']:8.2f}")
        if fees["ads"]:
            print(f"  - Offsite Ads (15%)                  ${fees['ads']:8.2f}")
        print(f"  - shipping label                     ${label:8.2f}")
        if uc is None:
            print(f"  - materials                          UNKNOWN - add {product} to costs.csv")
        else:
            print(f"  - materials                          ${materials:8.2f}")
        margin = profit / revenue * 100 if revenue else 0
        print(f"  = PROFIT                             ${profit:8.2f}   ({margin:.1f}% margin)")
        return

    rows = []
    with open(BASE / "orders.csv", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("date") and not row["date"].startswith("#"):
                rows.append(row)

    results = [analyze_order(r, costs) for r in rows]
    results.sort(key=lambda r: r["date"])

    print("=" * 78)
    print("PER-ORDER PROFIT  (newest last)")
    print("=" * 78)
    warn = []
    for r in results:
        mat = f"${r['materials']:7.2f}" if r["materials"] is not None else " UNKNOWN"
        flag = "  <-- add to costs.csv" if r["unknown_cost"] else ""
        if r["unknown_cost"]:
            warn.append(r["product"])
        margin = r["profit"] / r["revenue"] * 100 if r["revenue"] else 0
        print(f"{r['date']}  {r['platform']:<6} {r['product']:<20} x{r['qty']}  "
              f"rev ${r['revenue']:7.2f}  fees ${r['fees']:6.2f}  mat {mat}  "
              f"profit ${r['profit']:7.2f} ({margin:5.1f}%){flag}")

    print()
    print("=" * 78)
    print("MONTHLY SUMMARY")
    print("=" * 78)
    months = {}
    for r in results:
        m = r["date"][:7]
        d = months.setdefault(m, {"rev": 0.0, "fees": 0.0, "mat": 0.0, "ship": 0.0, "other": 0.0, "profit": 0.0, "n": 0, "unknown": False})
        d["rev"] += r["revenue"]; d["fees"] += r["fees"]; d["profit"] += r["profit"]; d["n"] += r["qty"]
        d["ship"] += r["label"]; d["other"] += r["other"]
        if r["materials"] is None:
            d["unknown"] = True
        else:
            d["mat"] += r["materials"]
    for m in sorted(months):
        d = months[m]
        margin = d["profit"] / d["rev"] * 100 if d["rev"] else 0
        unk = "  (some materials unknown - profit overstated)" if d["unknown"] else ""
        print(f"{m}:  {d['n']:3d} items  revenue ${d['rev']:8.2f}  platform fees ${d['fees']:7.2f}  "
              f"materials ${d['mat']:7.2f}  shipping ${d['ship']:6.2f}  "
              f"NET ${d['profit']:8.2f}  ({margin:.1f}% margin){unk}")

    tot = {"rev": sum(r["revenue"] for r in results), "profit": sum(r["profit"] for r in results),
           "fees": sum(r["fees"] for r in results)}
    if tot["rev"]:
        print()
        print(f"ALL TIME: revenue ${tot['rev']:.2f} | platform fees ${tot['fees']:.2f} "
              f"| NET PROFIT ${tot['profit']:.2f} ({tot['profit']/tot['rev']*100:.1f}% margin)")
    if warn:
        print()
        print("WARNING: no material costs found for: " + ", ".join(sorted(set(warn))))
        print("         Add them to costs.csv so profit isn't overstated.")
    if any(r["notes"].startswith("EXAMPLE") for r in rows if r.get("notes")):
        print()
        print("NOTE: example rows detected in orders.csv - numbers above are DEMO data.")


if __name__ == "__main__":
    main()
