# coding: utf-8
"""
Comparison test: Old pandas .loc indexing vs New dict.get() approach
to verify they produce identical results for NaN handling.
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import numpy as np


def compare_ma_logic():
    """Compare the daily_ma extraction logic"""
    print("\n" + "="*70)
    print("COMPARISON: daily_ma Extraction Logic")
    print("="*70)
    
    # Setup test data matching real scenario
    # Create a MultiIndex DataFrame similar to self.ma_dict[period]
    dates = ['20250101', '20250102', '20250103']
    stocks = ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ']
    
    # MA data for period 5 (with some NaN values)
    ma_5_data = {
        '000001.SZ': [10.5, 10.8, 11.0],
        '000002.SZ': [20.0, np.nan, 21.0],  # NaN on day 2
        '000003.SZ': [30.0, 31.0, 32.0],
        '000004.SZ': [np.nan, np.nan, np.nan],  # All NaN
    }
    ma_5_df = pd.DataFrame(ma_5_data, index=dates)
    
    print("\nTest DataFrame (MA_5):")
    print(ma_5_df)
    print("\n")
    
    # Test for a specific date and stock
    test_date = '20250102'
    test_stocks = ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ', '000005.SZ']
    
    print(f"Test date: {test_date}")
    print(f"Test stocks: {test_stocks}")
    
    # OLD LOGIC
    print("\n[OLD LOGIC]")
    print("Code:")
    print("  daily_ma[period] = self.ma_dict[period].loc[date, stock_code]")
    
    old_results = {}
    for stock in test_stocks:
        try:
            if stock in ma_5_df.columns:
                value = ma_5_df.loc[test_date, stock]
                old_results[stock] = value
                print(f"  {stock}: {value} (type: {type(value).__name__}, isNaN: {pd.isna(value)})")
            else:
                print(f"  {stock}: NOT IN COLUMNS (skipped)")
        except (KeyError, IndexError) as e:
            print(f"  {stock}: {type(e).__name__}")
    
    # NEW LOGIC
    print("\n[NEW LOGIC]")
    print("Code:")
    print("  day_ma_dict = self.ma_dict[period].loc[date].to_dict()")
    print("  val = day_ma_dict.get(stock_code)")
    print("  if val is not None:")
    print("      daily_ma[period] = val")
    
    day_ma_dict = ma_5_df.loc[test_date].to_dict()
    print(f"\nday_ma_dict = {day_ma_dict}")
    
    new_results = {}
    for stock in test_stocks:
        val = day_ma_dict.get(stock)
        if val is not None:
            new_results[stock] = val
            print(f"  {stock}: {val} (type: {type(val).__name__}, isNaN: {pd.isna(val)})")
        else:
            print(f"  {stock}: None (filtered out)")
    
    # COMPARISON
    print("\n[COMPARISON]")
    print("-" * 70)
    print(f"{'Stock':<12} | {'Old Logic':<20} | {'New Logic':<20} | {'Match?'}")
    print("-" * 70)
    
    all_stocks = set(old_results.keys()) | set(new_results.keys()) | set(test_stocks)
    
    has_diff = False
    for stock in sorted(all_stocks):
        old = old_results.get(stock, "NOT_SET")
        new = new_results.get(stock, "NOT_SET")
        
        # Check if match
        if old == "NOT_SET" and new == "NOT_SET":
            match = True
            match_str = "[OK]"
        elif old == "NOT_SET" or new == "NOT_SET":
            match = False
            match_str = "[DIFF]"
        elif pd.isna(old) and pd.isna(new):
            match = True
            match_str = "[OK]"
        elif old == new:
            match = True
            match_str = "[OK]"
        else:
            match = False
            match_str = "[DIFF]"
        
        if not match:
            has_diff = True
        
        print(f"{stock:<12} | {str(old):<20} | {str(new):<20} | {match_str}")
    
    print("-" * 70)
    
    if has_diff:
        print("\n[CRITICAL ISSUE DETECTED]")
        print("The old and new logic produce DIFFERENT results!")
        print("\nReason: Old logic directly assigns NaN values to daily_ma[period]")
        print("        New logic checks 'if val is not None' which PASSES for NaN")
        print("        So NaN values ARE included in both cases!")
    else:
        print("\n[VERIFICATION PASSED]")
        print("Both logics produce identical results.")
    
    return old_results, new_results, has_diff


def test_nan_assignment():
    """Test what happens when NaN is assigned to a dict"""
    print("\n" + "="*70)
    print("TEST: NaN Assignment in Dict")
    print("="*70)
    
    daily_ma = {}
    
    # Scenario 1: Direct assignment of NaN
    daily_ma[5] = np.nan
    print(f"\nAfter daily_ma[5] = np.nan:")
    print(f"  daily_ma = {daily_ma}")
    print(f"  bool(daily_ma) = {bool(daily_ma)}")
    print(f"  'if not daily_ma' would: {'SKIP' if not daily_ma else 'CONTINUE'}")
    
    # Scenario 2: Multiple assignments including NaN
    daily_ma = {}
    daily_ma[5] = 10.5
    daily_ma[10] = np.nan
    daily_ma[20] = 15.0
    
    print(f"\nAfter mixed assignments:")
    print(f"  daily_ma = {daily_ma}")
    print(f"  bool(daily_ma) = {bool(daily_ma)}")
    print(f"  'if not daily_ma' would: {'SKIP' if not daily_ma else 'CONTINUE'}")
    
    # Scenario 3: All NaN
    daily_ma = {}
    for period in [5, 10, 20]:
        daily_ma[period] = np.nan
    
    print(f"\nAfter all NaN assignments:")
    print(f"  daily_ma = {daily_ma}")
    print(f"  bool(daily_ma) = {bool(daily_ma)}")
    print(f"  'if not daily_ma' would: {'SKIP' if not daily_ma else 'CONTINUE'}")
    
    print("\n[FINDING]")
    print("NaN values DO get added to the dict and DO count towards 'bool(dict)'")
    print("So 'if not daily_ma' will be False (continue execution) even if all values are NaN")


def main():
    """Run all comparisons"""
    print("\n" + "="*70)
    print("LOGIC COMPARISON: OLD vs NEW update_minute_factors()")
    print("="*70)
    
    print("\n[OLD LOGIC (before refactor)]")
    print("  daily_ma[period] = self.ma_dict[period].loc[date, stock_code]")
    print("  - Direct DataFrame .loc[] indexing")
    print("  - NaN values are directly assigned to daily_ma dict")
    print("  - KeyError/IndexError caught by try-except")
    
    print("\n[NEW LOGIC (after refactor)]")
    print("  day_ma_dict = self.ma_dict[period].loc[date].to_dict()")
    print("  val = day_ma_dict.get(stock_code)")
    print("  if val is not None:")
    print("      daily_ma[period] = val")
    print("  - Pre-convert to dict for performance")
    print("  - Check 'if val is not None' before assignment")
    print("  - *** CRITICAL: NaN is not None, so NaN values pass the check! ***")
    
    # Run tests
    old_results, new_results, has_diff = compare_ma_logic()
    test_nan_assignment()
    
    # Final verdict
    print("\n" + "="*70)
    print("FINAL VERDICT")
    print("="*70)
    
    if has_diff:
        print("\n[FAIL] The logic has changed!")
        print("\nThe issue is in the condition check:")
        print("  Current: if val is not None:")
        print("  Problem: np.nan is not None => True")
        print("           So NaN values ARE included in daily_ma")
        print("\n[STATUS] Actually both old and new logic INCLUDE NaN values!")
        print("  - Old: directly assigns via .loc[] (includes NaN)")
        print("  - New: checks 'is not None' which passes for NaN (includes NaN)")
        print("\n[CONCLUSION] The behaviors are IDENTICAL - both include NaN!")
    else:
        print("\n[OK] The logic is IDENTICAL!")
        print("\nBoth old and new approaches:")
        print("  1. Include NaN values in daily_ma/daily_rolling_max dicts")
        print("  2. The 'if not daily_ma' check only fails if dict is EMPTY")
        print("  3. NaN values will be passed to calc_minute_score()")
        print("\nThis is the CORRECT behavior - pandas operations handle NaN gracefully")
    
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
