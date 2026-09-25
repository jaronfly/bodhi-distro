#!/usr/bin/env python3
"""
candle_profit.py -- real profit for a hand-poured candle shop.

Usage:
  python3 candle_profit.py --demo                        # generate demo data + full report
  python3 candle_profit.py --orders orders.csv --costs costs.csv [--fixed-costs 85]
       [--minutes-per-unit 18] [--wage 20] [--etsy-statement statement.csv]

Inputs:
  orders.csv   Etsy Order CSV export (Shop Manager -> Orders -> Download CSV,
               or Settings -> Options -> Data Downloads). Column names are
               matched fuzzily, so variations usually still work.
  costs.csv    Two columns: product,materials_cost  (per unit, wax+jar+wick+
               fragrance+label+packaging). Lines starting with # are ignored.
               Matching: exact item name first, then substring either way.

Fees (all editable via flags; Etsy US defaults):
  --transaction-pct 0.065   Etsy transaction fee on item price (excl. shipping)
  --listing-fee 0.20        renewal fee per unit sold
  --payment-pct 0.03 / --payment-flat 0.25   only used when the orders CSV
        has no actual "Card Processing Fees" column (actual value is used then)
  --offsite-ads-pct 0.15    applied to orders whose Order Type mentions "offsite"
  --etsy-statement FILE     monthly statement CSV; when given, the MONTHLY
        report swaps estimated listing/transaction/processing fees for the
        real totals parsed from the statement (per-order rows stay estimates).

Stdlib only. Python 3.8+.
"""
import argparse
import csv
import datetime as dt
import random
import sys
from collections import OrderedDict

# ---------------------------------------------------------------- utilities

def money(x):
    try:
        return float(str(x).replace("$", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0

def fmt(x):
    sign = "-" if x < 0 else ""
    return "%s$%.2f" % (sign, abs(x))

def find_col(headers, *keywords):
    """First header containing all keywords, case-insensitive."""
    kl = [k.lower() for k in keywords]
    for h in headers:
        hl = h.lower()
        if all(k in hl for k in kl):
            return h
    return None

def parse_date(s):
    s = (s or "").strip()
    for f in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(s, f)
        except ValueError:
            continue
    return None

def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

# ---------------------------------------------------------------- orders

def load_orders(path):
    rows = read_csv(path)
    if not rows:
        sys.exit("No rows found in %s" % path)
    h = rows[0].keys()
    c_date = find_col(h, "order", "date") or find_col(h, "date")
    c_oid = find_col(h, "order", "id")
    c_txn = find_col(h, "transaction", "id")
    c_item = find_col(h, "item", "name") or find_col(h, "item")
    c_var = find_col(h, "variation")
    c_qty = find_col(h, "quantity")
    c_price = find_col(h, "item", "price") or find_col(h, "price")
    c_ship = find_col(h, "shipping")
    c_disc = find_col(h, "discount")
    c_tax = find_col(h, "sales", "tax") or find_col(h, "tax")
    c_card = find_col(h, "processing") or find_col(h, "card")
    c_otype = find_col(h, "order", "type")
    c_coupon = find_col(h, "coupon")

    orders = OrderedDict()
    for i, r in enumerate(rows):
        oid = (r.get(c_oid) or r.get(c_txn) or ("row%d" % i)).strip()
        date = parse_date(r.get(c_date, "") or "")
        qty = int(money(r.get(c_qty, 1)) or 1)
        unit = money(r.get(c_price, 0))
        item = (r.get(c_item) or "Unknown item").strip()
        var = (r.get(c_var) or "").strip() if c_var else ""
        product = item + (" / " + var if var else "")
        line = {
            "product": product, "item": item, "qty": qty, "unit": unit,
            "gross": unit * qty,
            "discount": money(r.get(c_disc, 0)) if c_disc else 0.0,
        }
        o = orders.setdefault(oid, {
            "date": date, "lines": [], "shipping": 0.0, "card_fee": None,
            "order_type": "", "sales_tax": 0.0, "coupon": "",
        })
        o["lines"].append(line)
        if date and not o["date"]:
            o["date"] = date
        if c_ship and o["shipping"] == 0.0:          # order-level field repeats
            o["shipping"] = money(r.get(c_ship, 0))
        if c_card and o["card_fee"] is None:
            o["card_fee"] = money(r.get(c_card, 0))
        if c_otype and not o["order_type"]:
            o["order_type"] = (r.get(c_otype) or "").lower()
        if c_tax and o["sales_tax"] == 0.0:
            o["sales_tax"] = money(r.get(c_tax, 0))
        if c_coupon and not o["coupon"]:
            o["coupon"] = (r.get(c_coupon) or "").strip()
    return list(orders.values())

# ---------------------------------------------------------------- costs

def load_costs(path):
    costs = OrderedDict()
    for r in read_csv(path):
        name = (r.get("product") or "").strip()
        if not name or name.startswith("#"):
            continue
        costs[name] = money(r.get("materials_cost", r.get("cost", 0)))
    return costs

def match_cost(item, costs):
    if item in costs:
        return costs[item], "exact"
    il = item.lower()
    for name, c in costs.items():
        nl = name.lower()
        if nl and (nl in il or il in nl):
            return c, "partial"
    return None, None

# ---------------------------------------------------------------- analysis

def analyze(orders, costs, args):
    unmatched = OrderedDict()
    for o in orders:
        item_rev = sum(l["gross"] - l["discount"] for l in o["lines"])
        units = sum(l["qty"] for l in o["lines"])
        txn = sum(args.transaction_pct * l["gross"] for l in o["lines"])
        renew = sum(args.listing_fee * l["qty"] for l in o["lines"])
        if o["card_fee"] is None:
            card = args.payment_pct * (item_rev + o["shipping"]) + args.payment_flat
            card_src = "est"
        else:
            card = o["card_fee"]
            card_src = "actual"
        offsite = args.offsite_ads_pct * item_rev if "offsite" in o["order_type"] else 0.0
        materials = 0.0
        for l in o["lines"]:
            c, how = match_cost(l["item"], costs)
            if c is None:
                unmatched[l["item"]] = True
                c = 0.0
            l["unit_cost"] = c
            l["materials"] = c * l["qty"]
            l["fees"] = (args.transaction_pct + args.listing_fee) * l["gross"] \
                        if False else args.transaction_pct * l["gross"] + args.listing_fee * l["qty"]
            materials += l["materials"]
        o["units"] = units
        o["item_rev"] = item_rev
        o["revenue"] = item_rev + o["shipping"]
        o["fees"] = txn + renew + card + offsite
        o["fee_parts"] = {"txn": txn, "renew": renew, "card": card,
                          "card_src": card_src, "offsite": offsite}
        o["materials"] = materials
        o["net"] = o["revenue"] - o["fees"] - materials
        o["month"] = o["date"].strftime("%Y-%m") if o["date"] else "unknown"
    return list(unmatched.keys())

# ---------------------------------------------------------------- statements

def load_statement(path):
    """Returns {month: {fee_type_lower: total}} from an Etsy monthly statement CSV."""
    rows = read_csv(path)
    if not rows:
        return {}
    h = rows[0].keys()
    c_type = find_col(h, "type")
    c_amt = find_col(h, "amount")
    c_date = find_col(h, "date") or find_col(h, "month")
    out = {}
    for r in rows:
        d = parse_date(r.get(c_date, "") or "")
        month = d.strftime("%Y-%m") if d else "unknown"
        t = (r.get(c_type) or "").strip().lower()
        if not t:
            continue
        out.setdefault(month, {})
        out[month][t] = out[month].get(t, 0.0) + money(r.get(c_amt, 0))
    return out

def statement_fee_total(month_fees):
    """Sum fee-like types (listing, renewal, transaction, processing, offsite)."""
    keys = ("listing", "renewal", "transaction", "processing", "payment", "offsite")
    return sum(v for k, v in month_fees.items() if any(x in k for x in keys))

# ---------------------------------------------------------------- report

def report(orders, unmatched, args, statement=None):
    months = OrderedDict()
    for o in orders:
        m = months.setdefault(o["month"], {"orders": 0, "units": 0, "rev": 0.0,
                                           "fees": 0.0, "mat": 0.0})
        m["orders"] += 1
        m["units"] += o["units"]
        m["rev"] += o["revenue"]
        m["fees"] += o["fees"]
        m["mat"] += o["materials"]

    prods = OrderedDict()
    for o in orders:
        for l in o["lines"]:
            p = prods.setdefault(l["item"], {"units": 0, "rev": 0.0, "fees": 0.0,
                                             "mat": 0.0})
            p["units"] += l["qty"]
            p["rev"] += l["gross"] - l["discount"]
            p["fees"] += l["fees"]
            p["mat"] += l["materials"]

    W = 52
    def row(*cells):
        return "  " + "  ".join(str(c).ljust(w)[:w] for c, w in zip(cells, (14, 8, 8, 11, 11, 11, 11)))

    print("=" * 78)
    print("CANDLE PROFIT REPORT")
    print("=" * 78)
    print("Fee assumptions: transaction %.1f%% of item price | renewal %s/unit |" %
          (args.transaction_pct * 100, fmt(args.listing_fee)))
    print("payment %.1f%% + %s (actual CSV column used when present) | offsite ads %.0f%% on flagged orders"
          % (args.payment_pct * 100, fmt(args.payment_flat), args.offsite_ads_pct * 100))
    print("Fixed costs: %s/month | Labor: %s min/unit" %
          (fmt(args.fixed_costs), args.minutes_per_unit))
    if statement:
        print("Monthly statement supplied: monthly fee figures below are ACTUALS from it.")
    print()

    print("MONTHLY SUMMARY" + ("  (before labor)" if args.minutes_per_unit else ""))
    print(row("Month", "Orders", "Units", "Revenue", "Fees", "Materials", "Net"))
    tot = {"o": 0, "u": 0, "r": 0.0, "f": 0.0, "m": 0.0, "n": 0.0}
    for name, m in sorted(months.items()):
        fees = m["fees"]
        net = m["rev"] - fees - m["mat"] - args.fixed_costs
        if statement and name in statement:
            actual = statement_fee_total(statement[name])
            if actual:
                net = net + fees - actual  # swap estimate for actual
                fees = actual
        print(row(name, m["orders"], m["units"], fmt(m["rev"]), fmt(fees),
                  fmt(m["mat"]), fmt(net)))
        tot["o"] += m["orders"]; tot["u"] += m["units"]; tot["r"] += m["rev"]
        tot["f"] += fees; tot["m"] += m["mat"]; tot["n"] += net
    print(row("TOTAL", tot["o"], tot["u"], fmt(tot["r"]), fmt(tot["f"]),
              fmt(tot["m"]), fmt(tot["n"])))
    n_months = max(1, len(months))
    avg_net = tot["n"] / n_months
    per_order = tot["n"] / max(1, tot["o"])
    print()
    print("  Average net: %s/month | %s/order" % (fmt(avg_net), fmt(per_order)))
    print()

    print("PRODUCT SUMMARY (all months, variations grouped)")
    print("  " + "  ".join(str(c).ljust(w)[:w] for c, w in
          zip(("Product", "Units", "Margin", "Revenue", "Fees", "Materials", "Profit"),
              (28, 6, 7, 10, 10, 10, 10))))
    ranked = sorted(prods.items(), key=lambda kv: -(kv[1]["rev"] - kv[1]["fees"] - kv[1]["mat"]))
    for name, p in ranked:
        profit = p["rev"] - p["fees"] - p["mat"]
        margin = (profit / p["rev"] * 100) if p["rev"] else 0
        print("  " + "  ".join(str(c).ljust(w)[:w] for c, w in
              zip((name, p["units"], "%.0f%%" % margin, fmt(p["rev"]), fmt(p["fees"]),
                   fmt(p["mat"]), fmt(profit)), (28, 6, 7, 10, 10, 10, 10))))
    print()

    hours = tot["u"] * args.minutes_per_unit / 60.0
    print("VERDICT")
    if tot["n"] > 0:
        print("  Yes -- you are making money: %s net over %d month(s) (%s/month, %s/order),"
              % (fmt(tot["n"]), len(months), fmt(avg_net), fmt(per_order)))
        print("  after supplies, fees, and %s/month fixed costs, before paying yourself." %
              fmt(args.fixed_costs))
    else:
        print("  Not as it stands: %s net over %d month(s). Losses concentrated where margin %%"
              % (fmt(tot["n"]), len(months)))
        print("  is lowest above -- raise prices or cut materials there first.")
    if hours:
        eff_wage = tot["n"] / hours
        print("  At %d min/unit that's %.1f hours of labor -> effective earnings of %s/hour."
              % (args.minutes_per_unit, hours, fmt(eff_wage)))
        if args.wage:
            print("  If you paid yourself %s/hour, labor would cost %s -> bottom line %s."
                  % (fmt(args.wage), fmt(hours * args.wage), fmt(tot["n"] - hours * args.wage)))
    low = [n for n, p in ranked
           if p["rev"] and (p["rev"] - p["fees"] - p["mat"]) / p["rev"] < 0.30]
    if low:
        print("  Thin margins (<30%%): " + "; ".join(low))
    if unmatched:
        print()
        print("WARNING -- no materials cost matched for these items, so profit is")
        print("OVERSTATED until you add them to your costs file:")
        for u in unmatched:
            print("   - " + u)
    print("=" * 78)

# ---------------------------------------------------------------- demo data

DEMO_PRODUCTS = [
    ("Soy Candle 8oz - Amber Jar",   22.00, 4.85),
    ("Soy Candle 12oz - Clear Glass", 32.00, 6.40),
    ("Wax Melts 6-pack",             12.00, 2.10),
    ("Candle Gift Set (3)",          48.00, 12.75),
]
DEMO_HEADERS = ["Order Date","Order ID","Item Name","Variations","Item Price",
    "Quantity","Transaction ID","Buyer User ID","Ship To Name","Ship To City",
    "Ship To State","Ship To Zip","Ship To Country","Order Value","Coupon Code",
    "Discount Amount","Shipping","Sales Tax","Order Total","Card Processing Fees",
    "Order Type","Payment Type","Date Paid","Date Shipped"]

def make_demo(orders_path, costs_path):
    rng = random.Random(42)
    rows, oid = [], 3000
    months = [(6, "06"), (7, "07"), (8, "08")]
    for (mo, mm) in months:
        for _ in range(rng.randint(20, 25)):
            oid += 1
            day = rng.randint(1, 28)
            date = "2026-%s-%02d" % (mm, day)
            buyer = "buyer%d" % rng.randint(1000, 9999)
            offsite = "Offsite Ads Sale" if rng.random() < 0.12 else "Direct"
            n_lines = 2 if rng.random() < 0.15 else 1
            order_value, lines = 0.0, []
            for _ in range(n_lines):
                name, price, _c = rng.choice(DEMO_PRODUCTS)
                qty = rng.choice([1, 1, 1, 2, 3]) if "Melts" in name or "Gift" in name else 1
                var = rng.choice(["", "", "Scent: Cedar + Sage", "Scent: Amber + Oud",
                                  "Scent: Sea Salt"]) if "Candle" in name else ""
                lines.append((name, var, price, qty))
                order_value += price * qty
            coupon = "WELCOME10" if rng.random() < 0.18 else ""
            discount = round(0.10 * order_value, 2) if coupon else 0.0
            shipping = 0.0 if (order_value - discount) >= 35 else rng.choice([6.50, 7.25, 8.00])
            tax = round(0.0925 * (order_value - discount + shipping), 2)
            card = round(0.03 * (order_value - discount + shipping) + 0.25, 2)
            total = order_value - discount + shipping + tax
            for j, (name, var, price, qty) in enumerate(lines):
                d = discount if j == 0 else 0.0
                rows.append(dict(zip(DEMO_HEADERS, [
                    date, oid, name, var, "%.2f" % price, qty, oid * 10 + j, buyer,
                    "Jane Doe", "Portland", "OR", "97201", "United States",
                    "%.2f" % order_value, coupon, "%.2f" % d, "%.2f" % shipping,
                    "%.2f" % tax, "%.2f" % total, "%.2f" % card, offsite,
                    "Credit Card", date, date])))
    with open(orders_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DEMO_HEADERS)
        w.writeheader()
        w.writerows(rows)
    with open(costs_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["product", "materials_cost"])
        w.writerow(["# per-unit cost: wax + container + wick + fragrance + label + packaging"])
        for name, _p, c in DEMO_PRODUCTS:
            w.writerow([name, "%.2f" % c])
    print("Wrote %d order rows -> %s" % (len(rows), orders_path))
    print("Wrote costs      -> %s" % costs_path)

# ---------------------------------------------------------------- selftest

def selftest(orders_path):
    """Independently recompute the first order from raw CSV and compare."""
    rows = read_csv(orders_path)
    r = rows[0]
    qty = int(money(r["Quantity"])); unit = money(r["Item Price"])
    gross = unit * qty
    discount = money(r["Discount Amount"]); shipping = money(r["Shipping"])
    card = money(r["Card Processing Fees"])
    item_rev = gross - discount
    txn = 0.065 * gross; renew = 0.20 * qty
    offsite = 0.15 * item_rev if "offsite" in r["Order Type"].lower() else 0.0
    fees = txn + renew + card + offsite
    name = r["Item Name"]
    cost = dict((n, c) for n, _p, c in DEMO_PRODUCTS)[name]
    net = item_rev + shipping - fees - cost * qty
    return {"net": net, "fees": fees, "name": name, "qty": qty}

def check_selftest(orders, expected):
    o = orders[0]
    ok = abs(o["fees"] - expected["fees"]) < 0.01 and abs(o["net"] - expected["net"]) < 0.01
    print("SELFTEST: first order %s qty=%d  fees %s vs %s | net %s vs %s -> %s"
          % (expected["name"], expected["qty"], fmt(o["fees"]), fmt(expected["fees"]),
             fmt(o["net"]), fmt(expected["net"]), "PASS" if ok else "FAIL"))
    if not ok:
        sys.exit(1)

# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Real profit for a candle shop.")
    ap.add_argument("--orders")
    ap.add_argument("--costs")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--fixed-costs", type=float, default=0.0)
    ap.add_argument("--minutes-per-unit", type=int, default=0)
    ap.add_argument("--wage", type=float, default=0.0)
    ap.add_argument("--transaction-pct", type=float, default=0.065)
    ap.add_argument("--listing-fee", type=float, default=0.20)
    ap.add_argument("--payment-pct", type=float, default=0.03)
    ap.add_argument("--payment-flat", type=float, default=0.25)
    ap.add_argument("--offsite-ads-pct", type=float, default=0.15)
    ap.add_argument("--etsy-statement")
    args = ap.parse_args()

    if args.demo:
        args.orders, args.costs = "demo_orders.csv", "demo_costs.csv"
        make_demo(args.orders, args.costs)
        args.fixed_costs = args.fixed_costs or 85.0
        args.minutes_per_unit = args.minutes_per_unit or 18
    if not (args.orders and args.costs):
        sys.exit("Need --orders and --costs (or --demo). See --help.")

    orders = load_orders(args.orders)
    costs = load_costs(args.costs)
    unmatched = analyze(orders, costs, args)
    statement = load_statement(args.etsy_statement) if args.etsy_statement else None

    print()
    report(orders, unmatched, args, statement)

    if args.demo:
        print()
        check_selftest(orders, selftest(args.orders))

if __name__ == "__main__":
    main()
