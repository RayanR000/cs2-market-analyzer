# Getting Historical Price Data - Step by Step

Choose one of these approaches based on your needs and available resources.

## 🟢 Option 1: Kaggle Datasets (Easiest, Free)

**Best for:** Getting started quickly with pre-collected data

### Step 1: Check Available Datasets
```bash
cd backend
source venv/bin/activate
python scripts/download_kaggle_datasets.py --list
```

### Step 2: Create Kaggle Account
1. Sign up at https://kaggle.com (free)
2. Go to Account > API
3. Click "Create New Token" to download `kaggle.json`
4. Move it to `~/.kaggle/kaggle.json`:
   ```bash
   mkdir -p ~/.kaggle
   mv ~/Downloads/kaggle.json ~/.kaggle/
   chmod 600 ~/.kaggle/kaggle.json
   ```

### Step 3: Install Kaggle CLI
```bash
pip install kaggle
```

### Step 4: Download a Dataset
Look for these popular datasets:
- **steam-community-market-history** - Most comprehensive
- **csgo-price-history** - CS:GO specific
- **csgo-weapon-cases** - Case and item data

```bash
python scripts/download_kaggle_datasets.py --dataset muonneutrino/steam-community-market-history
```

### Step 5: Import to Your Database
```bash
python scripts/import_historical_prices.py --source csv --file data/kaggle/prices.csv
```

**Timeline:** 30 minutes
**Data coverage:** 2015-2023 (typical)
**Effort:** Low

---

## 🟡 Option 2: Wayback Machine Snapshots (Free, More Work)

**Best for:** Specific items or gaps in other data

### Step 1: Find Available Snapshots
```bash
python scripts/scrape_wayback_machine.py --sample
```

This will:
- Check popular CS:GO items on Wayback Machine
- Find available snapshots from 2015-2023
- Create CSV with Wayback URLs

### Step 2: Manually Extract Prices
The script generates URLs like:
```
https://web.archive.org/web/20200115120000/steamcommunity.com/market/listings/730/AK-47%20%7C%20Phantom%20Disruptor
```

For each snapshot:
1. Click the link in your browser
2. Look for the price/volume info
3. Manually note the price and date

Example output format:
```csv
item_name,timestamp,price,volume,source
AK-47 | Phantom Disruptor,2020-01-15T12:00:00,3.50,1200,wayback_machine
M4A4 | Uncharted,2020-01-15T12:00:00,4.25,850,wayback_machine
```

### Step 3: Save as CSV
Create a file `data/wayback_prices.csv` with the data

### Step 4: Import
```bash
python scripts/import_historical_prices.py --source csv --file data/wayback_prices.csv
```

**Timeline:** 2-3 hours (manual extraction)
**Data coverage:** 2013-2023 (spotty)
**Effort:** Medium

---

## 🔴 Option 3: BitSkins API (Best Quality, Requires Registration)

**Best for:** Most comprehensive and accurate data

### Step 1: Request BitSkins API Access
1. Go to https://bitskins.com
2. Contact support for API access
3. They may require:
   - Account verification
   - API key request
   - Possible fee for historical data

### Step 2: Authentication
Once you have API key:
```bash
export BITSKINS_API_KEY="your_api_key_here"
```

### Step 3: Fetch Data
Create a script like this:
```python
import requests
import csv

API_KEY = "your_api_key"
APP_ID = 730  # CS:GO/CS2

# Example: Get prices for specific item
response = requests.get(
    "https://api.bitskins.com/api/v1/market/price_data",
    params={
        "app_id": APP_ID,
        "market_hash_name": "AK-47 | Phantom Disruptor",
        "time_period": "7d",
        "api_key": API_KEY
    }
)

data = response.json()
# Parse and save to CSV
```

### Step 4: Format and Import
Once you have CSV:
```bash
python scripts/import_historical_prices.py --source csv --file data/bitskins_prices.csv
```

**Timeline:** 1-2 weeks (waiting for API approval)
**Data coverage:** 2015-2023 (complete)
**Effort:** Low (after setup)

---

## Quick Comparison

| Source | Time to Data | Coverage | Quality | Effort |
|--------|-------------|----------|---------|--------|
| **Kaggle** | 30 min | 2015-2023 | Medium | Low |
| **Wayback** | 2-3 hrs | 2013-2023 | Low-Med | Medium |
| **BitSkins** | 1-2 weeks | 2015-2023 | High | Low |

---

## Recommended Path

### Start Here (30 minutes):
```bash
# Try Kaggle first - easiest, quickest results
pip install kaggle
python scripts/download_kaggle_datasets.py --list
# Follow the download steps above
```

### If Kaggle Data Works:
You'll have 2+ years of historical prices ready for analysis

### To Fill Gaps:
Use Wayback Machine for specific items missing from Kaggle

### For Production Use:
Request BitSkins API for most comprehensive data

---

## Testing Your Data

Once imported, verify it worked:

```bash
# Check how many price records you have
source venv/bin/activate
python << 'EOF'
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
result = db.execute(text('SELECT COUNT(*) FROM price_history'))
count = result.scalar()

result = db.execute(text('SELECT MIN(created_at), MAX(created_at) FROM price_history'))
min_date, max_date = result.fetchone()

print(f"Total prices: {count}")
print(f"Date range: {min_date} to {max_date}")

db.close()
EOF
```

Expected output:
```
Total prices: 500,000+
Date range: 2015-01-01 to 2026-05-22
```

---

## Next Steps

Once you have historical data:
1. ✅ Verify it imported correctly
2. ✅ Run analysis to see event correlation:
   ```bash
   python scripts/analyze_events_impact.py --days 3650
   ```
3. ✅ Build prediction model with full historical context

---

## Troubleshooting

**"No datasets found on Kaggle"**
- Try different search terms: "steam market", "csgo prices", "counter strike"
- Filter by recency (newest first)

**"Wayback Machine URL doesn't load"**
- Item may not have been on Steam Market then
- Try different years or items
- Some snapshots may be incomplete

**"Import fails with 'Item not found'"**
- Check spelling of item names in CSV
- Item names must match exactly in database
- Run a sample first (10-20 items) to verify format

**"BitSkins API declined"**
- Contact them for alternative access
- Consider combining Kaggle + Wayback data instead
