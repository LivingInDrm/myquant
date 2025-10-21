# Agent Development Rules

## Windows Python Output Rules

### Core Issue
Windows console uses GBK encoding. Unicode special characters cause `UnicodeEncodeError` crashes.

### Requirements

**❌ NEVER use:** Unicode symbols like `✓ ✗ ⚠️ ❌ ✅`

**✅ Use ASCII alternatives:**
```python
print("[OK] Success")      # Don't use ✓
print("[FAIL] Failed")     # Don't use ✗
print("[WARN] Warning")    # Don't use ⚠️
print("[INFO] Info")
```

**✅ Chinese text is OK:** May display garbled but won't crash

**✅ File header:** `#coding: utf-8`

### Fix Chinese Garbled Text

Add to script header to force UTF-8 output encoding:

```python
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

**Why:**
- Windows PowerShell defaults to GBK encoding
- Python outputs UTF-8, causing garbled Chinese characters
- This wrapper forces UTF-8 without affecting system settings
- Portable: works on any machine without user configuration

## XTQuant API Reference

### Environment
QMT (the platform xtquant depends on) is already running with account: `2046115`

### Virtual Environment
All Python dependencies are in venv. **Must activate venv before running any Python scripts:**

```powershell
.\venv\Scripts\Activate.ps1
```

```cmd
deactivate
```

### Documentation
For xtquant API references, check the documentation in the `docs/` directory:
- `docs/xtdata.md` - Complete data interface documentation
- `docs/xtdata_market_api.md` - Market data API
- `docs/xtdata_stock_data_api.md` - Stock data API
- `docs/xttrader.md` - Trading interface documentation

### Source Code
For more detailed xtquant implementation details, refer to the source code in the `xtquant/` directory:
- `xtquant/xtdata.py` - Data interface implementation
- `xtquant/xttrader.py` - Trading interface implementation
- `xtquant/xttype.py` - Data type definitions
- `xtquant/xtconstant.py` - Constant definitions


## Backtest Debugging Lessons

### Issue 1: Insufficient Warmup Data

**Problem:** Factor calculation requires historical data (e.g., MA120 needs 120 days), but backtest period was only 2 days, causing all buy signals to be zero.

**Root Cause:** Data fetch window equals backtest window, no warmup period.

**Solution:** 
```python
warmup_days = 365  # ~250 trading days
data_start = backtest_start - timedelta(days=warmup_days)
```

**Key Point:** Decouple data fetch window from backtest execution window.

### Issue 2: Date Filter Logic Bug

**Problem:** Filter function marked stocks at listing date using `df.at[listing_date, stock] = 1`, then used `ffill()` + `expanding().sum()` to count days. When listing date was before data range (e.g., old stocks from 1990s), `KeyError` occurred, causing all old stocks to be incorrectly filtered.

**Symptom:** 600928 (listed 1990s) marked as "insufficient listing days", while it traded for 30+ years.

**Root Cause:** Logic relied on listing date being within data range to mark the starting point.

**Solution:** Calculate date difference directly without relying on data range:
```python
for date in df.index:
    days_since_listing = (current_date - listing_date).days
    if days_since_listing >= threshold:
        result[date, stock] = True
```

**Key Point:** Time-based filters should use absolute date calculation, not data-range-dependent tricks.

### Debugging Strategy

1. Add progressive logging at each filter stage:
   - Total candidates
   - After condition 1
   - After condition 2  
   - After listing filter
2. Print filtered-out items with reasons
3. Verify assumptions: check if "new stocks" are actually new

