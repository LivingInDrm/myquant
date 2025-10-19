# Minute-Level Handlebar Refactor Plan

## Goals
- Process one bar per `handlebar` invocation instead of scanning the entire trading day.
- Align backtest flow with real-time execution semantics, enabling incremental logging and easier transition to live trading.
- Maintain existing strategy logic while introducing reliable minute-data caching and state management.

---

## Architecture Overview
1. **Minute-period backtest**
   - Run the main script with `period='1m'` so the engine advances bar-by-bar.
   - Ensure historical minute data for the reference symbol is available across the full backtest window.

2. **On-demand minute data cache**
   - Maintain a dict `g.minute_data_cache` keyed by trading date.
   - When the callback detects a new trading day, load that day’s 1-minute data via `DataProvider.get_minute_data`.
   - Optionally discard previous dates from the cache to avoid unbounded memory growth.

3. **Per-day state reset**
   - Track `g.current_trading_date`. When `handlebar` sees a date change:
     - Skip processing if the date is outside the backtest range.
     - Optionally perform open-phase actions (e.g., selling previous holdings) with a clearly defined price source.
     - Reset a lightweight day-state object (`g.day_state`) with fields such as `buy_count`, `minute_counter`, or any flags needed for the day.
     - Reinitialize strategy minute caches by calling `g.strategy.init_minute_cache(date, g.stock_list)`.

4. **Per-bar processing**
   - For each `handlebar` call:
     1. Resolve `current_timestamp = C.get_bar_timetag(C.barpos)` and derive `current_date` and `current_time`.
     2. Fetch the minute row from `g.minute_data_cache[current_date]`. Guard against missing entries (market halts, data gaps).
     3. Update any cumulative intraday metrics if the strategy needs them. Prefer to keep strategy-specific rolling state inside the strategy object.
     4. Invoke `g.strategy.update_minute_factors(...)` with the current price/volume/amount snapshot.
     5. Pull latest holdings/cash from `TradeExecutor` and generate buy/sell signals for this minute only.
     6. Execute orders immediately, then update strategy and global state accordingly.
     7. Emit optional debug logs (e.g., new deals since last bar) for easier inspection.

5. **Strategy adjustments**
   - Ensure `MomentumStrategy` methods accept minute-level updates without requiring a full-day dataset.
   - Reinforce encapsulation: state that directly influences signals (rolling averages, minute caches) should stay inside the strategy. The main script passes in required numbers instead of giving the strategy a pointer to `g`.

6. **Order/deal tracking**
   - Because the engine may not populate `ORDER`/`DEAL` tables mid-day, maintain an in-memory trade log if real-time diagnostics are needed.
   - Alternatively, poll `get_trade_detail_data(..., 'ORDER'/'DEAL', ...)` at the end of each bar and report deltas; expect non-empty data only if the runtime supports it.

---

## Implementation Steps
1. **Global initialization**
   - In `init()`, define `g.minute_data_cache = {}`, `g.current_trading_date = None`, and `g.day_state = {}`.

2. **Day transition helper**
   - Create a helper function `start_new_trading_day(current_date, C)` that:
     - Loads minute data for the date if not cached.
     - Handles opening actions (e.g., sell signals) using current holdings.
     - Resets `g.day_state` and strategy caches.

3. **Handlebar refactor**
   - Replace the “full-day loop” with per-bar logic described above.
   - Guard against missing minute data; when absent, return early to avoid exceptions.
   - Update buy-count and any other daily counters directly after each order.

4. **Strategy updates**
   - Review `MomentumStrategy.update_minute_factors` to ensure it can digest a single-minute snapshot.
   - If cumulative stats are required, expose methods to update them per minute rather than recalculating from scratch.

5. **Optional cleanup**
   - After the last bar of a trading day (detect via `C.is_last_bar()` or by comparing next bar date), prune `g.minute_data_cache` for older dates if memory pressure is a concern.

---

## Validation Checklist
- Backtest with a short date range and confirm:
  - `handlebar` logs appear once per minute.
  - Holdings/cash snapshots reflect intra-day trades immediately.
  - Daily counters reset correctly at the first bar of each trading day.
- Stress-test with a longer period to ensure minute-data caching does not exhaust memory (monitor peak usage).
- Compare profitability metrics before/after refactor to confirm behavioral parity, allowing for timing differences introduced by per-bar execution.

---

## Risks & Mitigations
- **Minute data availability**: verify data ingestion before the run; add graceful handling for missing bars.
- **State drift**: clearly separate global orchestration state (e.g., cached data) from strategy signal state to avoid inconsistent calculations.
- **Order execution timing**: document the exact price source for opening/closing trades to keep results deterministic and auditable.

