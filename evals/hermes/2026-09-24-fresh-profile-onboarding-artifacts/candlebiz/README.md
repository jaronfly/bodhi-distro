# Candlebiz - profit clarity for your candle shop

Three files, that's it:

- costs.csv      - what each product costs you to MAKE (edit the sample numbers to your real costs)
- orders.csv     - one line per order (replace the EXAMPLE rows with real orders)
- profit.py      - runs the math

## Everyday use

1. After an order, add one line to orders.csv:
   date,platform,product,qty,item_total,shipping_charged,gift_wrap_charged,shipping_label_cost,offsite_ad,other_fees,notes
   e.g.  2026-09-24,etsy,AMBER-8OZ,1,28.00,0.00,0.00,6.40,no,0.00,

2. See if you're making money:
   python3 profit.py

3. Test a price before you list it:
   python3 profit.py scenario <item_total> <shipping_charged> <label_cost> <product> [offsite]
   e.g. python3 profit.py scenario 32 0 6.40 AMBER-8OZ offsite

## Fee model baked in (US Etsy, verified Sep 2026)
- $0.20 listing renewal per item sold
- 6.5% transaction fee on item + shipping charged + gift wrap
- 3% + $0.25 payment processing on the order total
- 15% Offsite Ads fee when an order is ad-attributed (set offsite_ad to "yes")
- platform "direct" (markets, your own site) = no platform fees

Tip: prices ending in odd cents and free-shipping listings change the fee base -
use "scenario" to compare before you commit. Batch/multi-item orders: set qty
and item_total to the whole order; listing renewal is charged per item.
