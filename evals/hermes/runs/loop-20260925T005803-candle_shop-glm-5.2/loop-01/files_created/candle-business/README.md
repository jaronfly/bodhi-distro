# Candle shop profit kit

Answer: "am I actually making money after supplies and fees?"

## Files

- config.csv      -- fee rates and monthly fixed costs. The Etsy rates (verified
                     Sept 2026) are pre-filled; edit the rest.
- products.csv    -- one row per product: price, what you charge for shipping,
                     your material cost per unit, shipping label cost, packaging
                     cost, and estimated units sold per month.
- orders.csv      -- REAL orders go here, one per line:
                     date, product (match products.csv name), qty,
                     item_total (price x qty), shipping_charged, offsite_ad (yes/no).
                     Once this has rows, run "actual" mode to use real numbers.
- monthly_costs.csv -- one-off monthly expenses (market fees, a bulk wax order,
                     software, etc.) as month, description, amount.

## Run

    python3 profit.py           # estimate mode (from products.csv volumes)
    python3 profit.py actual    # actual mode (from orders.csv)

Everything is USD. Fees modeled: $0.20 listing per unit sold, 6.5% transaction
on item + shipping charged, 3% + $0.25 processing on order total, optional
15% offsite-ads fee on a share of orders (set the share in config.csv).

Reminder: under $10k trailing-365-day sales, you can opt out of Offsite Ads
in Shop Manager > Settings > Offsite Ads.
