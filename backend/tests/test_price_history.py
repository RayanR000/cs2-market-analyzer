"""
Test Steam pricehistory API with authenticated session.
Compares data with existing DB records.
"""
import sys
import os
import time
import json
from datetime import datetime
import requests

sys.path.insert(0, '.')
from database import SessionLocal, Item, PriceHistory

TEST_ITEMS = [
    "AK-47 | Redline (Field-Tested)",
    "AWP | Asiimov (Field-Tested)",
    "AK-47 | The Empress (Field-Tested)",
    "M4A1-S | Hyper Beast (Field-Tested)",
    "Desert Eagle | Blaze (Factory New)",
]

DELAY_BETWEEN = 10.0

db = SessionLocal()

print(f"{'='*90}")
print(f"{'ITEM':55s} | {'API Records':>12s} | {'DB Records':>10s}")
print(f"{'='*90}")

for idx, item_name in enumerate(TEST_ITEMS):
    if idx > 0:
        print(f"  ... waiting {DELAY_BETWEEN}s before next request ...")
        time.sleep(DELAY_BETWEEN)

    url = "https://steamcommunity.com/market/pricehistory/"
    params = {"appid": 730, "market_hash_name": item_name}
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://steamcommunity.com/market/",
    }

    try:
        resp = requests.get(
            url, params=params, headers=headers, timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
        else:
            data = None
    except Exception as e:
        resp = None
        data = None

    print(f"\n--- {item_name} ---")

    if data and data.get("success"):
        prices = data.get("prices", [])
        api_count = len(prices)
        print(f"  API records: {api_count}")
        if prices:
            print(f"  Date range: {prices[0][0]} -> {prices[-1][0]}")
            print(f"  Price range: ${float(prices[0][1]):.2f} -> ${float(prices[-1][1]):.2f}")
            print(f"  Currency suffix: '{data.get('price_suffix', '')}'")
    else:
        api_count = 0
        status = resp.status_code if resp else "error"
        body = resp.text[:200] if resp else ""
        print(f"  API FAILED (status={status}): {body}")

    item = db.query(Item).filter(Item.item_id == item_name).first()
    if item:
        ph = db.query(PriceHistory).filter(PriceHistory.item_id == item.id).order_by(PriceHistory.timestamp)
        db_count = ph.count()
        print(f"  DB records: {db_count}")
        if db_count > 0:
            first = ph.first()
            last = ph.order_by(PriceHistory.timestamp.desc()).first()
            print(f"  DB date range: {first.timestamp.strftime('%Y-%m-%d')} -> {last.timestamp.strftime('%Y-%m-%d')}")
            print(f"  DB price range: ${first.price:.2f} -> ${last.price:.2f}")
    else:
        print(f"  DB: item not found")

db.close()

print(f"\n{'='*90}")
print("Done.")
