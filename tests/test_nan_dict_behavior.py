# coding: utf-8
"""
Test script to verify pandas Series.to_dict() NaN handling behavior
and dict.get() return behavior for NaN values.

This validates the logic change in update_minute_factors() where:
- Before: day_avg_vol_5d[stock_code] (Series indexing)
- After: day_avg_vol_5d.get(stock_code) (dict.get after to_dict())
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import numpy as np


def test_series_to_dict_nan_handling():
    """Test 1: Verify that Series.to_dict() preserves NaN values"""
    print("\n" + "="*70)
    print("TEST 1: Series.to_dict() NaN Preservation")
    print("="*70)
    
    # Create Series with NaN values
    series = pd.Series({
        'stock_A': 100.0,
        'stock_B': np.nan,
        'stock_C': 0.0,
        'stock_D': 200.0,
        'stock_E': np.nan
    })
    
    print("\nOriginal Series:")
    print(series)
    print("\nSeries types:")
    for key, value in series.items():
        print(f"  {key}: {type(value).__name__} = {value}")
    
    # Convert to dict
    series_dict = series.to_dict()
    
    print("\nAfter to_dict():")
    print(series_dict)
    print("\nDict value types:")
    for key, value in series_dict.items():
        print(f"  {key}: {type(value).__name__} = {value}")
    
    # Verify NaN preservation
    print("\n[VERIFICATION]")
    print(f"  stock_B is NaN in Series: {pd.isna(series['stock_B'])}")
    print(f"  stock_B is NaN in Dict: {pd.isna(series_dict['stock_B'])}")
    print(f"  stock_E is NaN in Series: {pd.isna(series['stock_E'])}")
    print(f"  stock_E is NaN in Dict: {pd.isna(series_dict['stock_E'])}")
    
    return series, series_dict


def test_dict_get_with_nan():
    """Test 2: Verify dict.get() behavior with NaN values"""
    print("\n" + "="*70)
    print("TEST 2: dict.get() Behavior with NaN Values")
    print("="*70)
    
    # Create dict with NaN
    test_dict = {
        'exists_normal': 100.0,
        'exists_nan': np.nan,
        'exists_zero': 0.0
    }
    
    print("\nTest dictionary:")
    print(test_dict)
    
    # Test different scenarios
    test_cases = [
        ('exists_normal', 'Key exists with normal value'),
        ('exists_nan', 'Key exists with NaN value'),
        ('exists_zero', 'Key exists with zero value'),
        ('not_exists', 'Key does not exist'),
    ]
    
    print("\n[DICT.GET() RESULTS]")
    for key, description in test_cases:
        result = test_dict.get(key)
        result_type = type(result).__name__
        is_none = result is None
        is_nan = pd.isna(result) if result is not None else False
        
        print(f"\n  {description}:")
        print(f"    key: '{key}'")
        print(f"    result: {result}")
        print(f"    type: {result_type}")
        print(f"    is None: {is_none}")
        print(f"    is NaN (pd.isna): {is_nan}")
    
    return test_dict


def test_old_vs_new_logic():
    """Test 3: Compare old Series indexing vs new dict.get() logic"""
    print("\n" + "="*70)
    print("TEST 3: Old Logic vs New Logic Comparison")
    print("="*70)
    
    # Create test data matching the strategy scenario
    day_avg_vol_5d_series = pd.Series({
        '000001.SZ': 1000000.0,
        '000002.SZ': np.nan,  # NaN case
        '000003.SZ': 0.0,      # Zero case
        '000004.SZ': 500000.0,
    })
    
    print("\nTest data (day_avg_vol_5d Series):")
    print(day_avg_vol_5d_series)
    
    # Convert to dict for new logic
    day_avg_vol_5d_dict = day_avg_vol_5d_series.to_dict()
    
    print("\nAfter to_dict():")
    print(day_avg_vol_5d_dict)
    
    # Test stocks
    test_stocks = ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ', '000005.SZ']
    
    print("\n[COMPARISON TABLE]")
    print("-" * 100)
    print(f"{'Stock':<12} | {'Old: series[key]':<20} | {'New: dict.get(key)':<20} | {'Match?':<8} | {'Notes'}")
    print("-" * 100)
    
    results = []
    for stock in test_stocks:
        # OLD LOGIC: series[stock_code]
        try:
            old_result = day_avg_vol_5d_series[stock]
            old_value = old_result
            old_str = f"{old_value}"
        except KeyError:
            old_value = None
            old_str = "KeyError"
        
        # NEW LOGIC: dict.get(stock_code)
        new_value = day_avg_vol_5d_dict.get(stock)
        new_str = f"{new_value}"
        
        # Check if values match
        if old_value is None and new_value is None:
            match = True
            notes = "Both None (key missing)"
        elif old_value is not None and new_value is not None:
            if pd.isna(old_value) and pd.isna(new_value):
                match = True
                notes = "Both NaN"
            elif old_value == new_value:
                match = True
                notes = "Values equal"
            else:
                match = False
                notes = f"DIFF: {old_value} != {new_value}"
        else:
            match = False
            notes = f"DIFF: one is None"
        
        match_str = "[OK]" if match else "[FAIL]"
        print(f"{stock:<12} | {old_str:<20} | {new_str:<20} | {match_str:<8} | {notes}")
        
        results.append({
            'stock': stock,
            'old': old_value,
            'new': new_value,
            'match': match
        })
    
    print("-" * 100)
    
    return results


def test_conditional_logic():
    """Test 4: Verify the conditional logic 'if val is not None'"""
    print("\n" + "="*70)
    print("TEST 4: Conditional Logic - 'if val is not None'")
    print("="*70)
    
    test_dict = {
        'normal': 100.0,
        'nan': np.nan,
        'zero': 0.0
    }
    
    print("\nTest dictionary:")
    print(test_dict)
    
    print("\n[CONDITIONAL CHECKS]")
    
    test_keys = ['normal', 'nan', 'zero', 'missing']
    
    print("\nCode: val = dict.get(key); if val is not None: ...")
    print("-" * 70)
    print(f"{'Key':<12} | {'dict.get()':<15} | {'is not None':<12} | {'pd.isna()':<12} | {'Pass Filter?'}")
    print("-" * 70)
    
    for key in test_keys:
        val = test_dict.get(key)
        not_none = val is not None
        is_nan = pd.isna(val) if val is not None else "N/A"
        pass_filter = not_none  # This is what the code checks
        
        print(f"{key:<12} | {str(val):<15} | {str(not_none):<12} | {str(is_nan):<12} | {pass_filter}")
    
    print("-" * 70)
    
    # Critical test: NaN values
    print("\n[CRITICAL FINDING]")
    nan_val = test_dict.get('nan')
    print(f"  For key='nan': dict.get() returns {nan_val}")
    print(f"  Type: {type(nan_val)}")
    print(f"  'nan_val is not None' = {nan_val is not None}")
    print(f"  'pd.isna(nan_val)' = {pd.isna(nan_val)}")
    print()
    print("  [WARN] NaN is not None! So 'if val is not None' will be True for NaN values.")
    print("  This means NaN values WILL pass the 'if val is not None' check.")


def test_full_filtering_logic():
    """Test 5: Simulate the complete filtering logic from update_minute_factors"""
    print("\n" + "="*70)
    print("TEST 5: Full Filtering Logic Simulation")
    print("="*70)
    
    # Setup test data
    day_avg_vol_5d_series = pd.Series({
        '000001.SZ': 1000000.0,  # Normal case
        '000002.SZ': np.nan,      # NaN case - should be filtered
        '000003.SZ': 0.0,         # Zero case - should be filtered
        '000004.SZ': -100.0,      # Negative case - should be filtered
        '000005.SZ': 500000.0,    # Normal case
    })
    
    print("\nInput Series (day_avg_vol_5d):")
    print(day_avg_vol_5d_series)
    
    # Convert to dict
    day_avg_vol_5d_dict = day_avg_vol_5d_series.to_dict()
    
    stocks = list(day_avg_vol_5d_series.index)
    
    print("\n[OLD LOGIC SIMULATION]")
    print("Code: avg_vol = day_avg_vol_5d[stock_code]; if pd.isna(avg_vol) or avg_vol <= 0: continue")
    
    old_passed = []
    for stock in stocks:
        try:
            avg_vol = day_avg_vol_5d_series[stock]
            if pd.isna(avg_vol) or avg_vol <= 0:
                print(f"  {stock}: FILTERED (value={avg_vol})")
            else:
                print(f"  {stock}: PASSED (value={avg_vol})")
                old_passed.append(stock)
        except KeyError:
            print(f"  {stock}: FILTERED (KeyError)")
    
    print("\n[NEW LOGIC SIMULATION]")
    print("Code: avg_vol = dict.get(stock_code); if avg_vol is None or pd.isna(avg_vol) or avg_vol <= 0: continue")
    
    new_passed = []
    for stock in stocks:
        avg_vol = day_avg_vol_5d_dict.get(stock)
        if avg_vol is None or pd.isna(avg_vol) or avg_vol <= 0:
            print(f"  {stock}: FILTERED (value={avg_vol})")
        else:
            print(f"  {stock}: PASSED (value={avg_vol})")
            new_passed.append(stock)
    
    print("\n[VERIFICATION]")
    print(f"  Old logic passed: {old_passed}")
    print(f"  New logic passed: {new_passed}")
    print(f"  Results match: {old_passed == new_passed}")
    
    return old_passed, new_passed


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("PANDAS SERIES.TO_DICT() NAN HANDLING VERIFICATION")
    print("="*70)
    print("\nPurpose: Verify that the refactored update_minute_factors() logic")
    print("         produces identical results to the original implementation.")
    print("\nOriginal: avg_vol_5d[stock_code]  (Series indexing)")
    print("Modified: avg_vol_5d.get(stock_code)  (dict.get after to_dict())")
    
    # Run all tests
    test_series_to_dict_nan_handling()
    test_dict_get_with_nan()
    test_old_vs_new_logic()
    test_conditional_logic()
    old_passed, new_passed = test_full_filtering_logic()
    
    # Final summary
    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    
    print("\n[KEY FINDINGS]")
    print("1. Series.to_dict() PRESERVES NaN values (they don't become None)")
    print("2. dict.get(key) returns NaN if key exists with NaN value")
    print("3. dict.get(key) returns None if key doesn't exist")
    print("4. 'np.nan is not None' evaluates to True")
    print("5. Therefore: 'if val is not None' will PASS for NaN values!")
    
    print("\n[CRITICAL ISSUE IDENTIFIED]")
    print("The code at lines 199 and 206 uses:")
    print("    if val is not None:")
    print("        daily_ma[period] = val")
    print()
    print("This WILL include NaN values, which may not be the intended behavior.")
    print("The original code likely benefited from automatic NaN propagation in pandas.")
    
    print("\n[RECOMMENDATION]")
    print("Change the condition from:")
    print("    if val is not None:")
    print("to:")
    print("    if val is not None and not pd.isna(val):")
    print()
    print("OR, to match the exact logic used for avg_vol_per_min_5d at line 183:")
    print("    if val is None or pd.isna(val):")
    print("        continue")
    
    print("\n[STATUS]")
    if old_passed == new_passed:
        print("[OK] For the primary filtering logic (avg_vol_5d), results are identical.")
    else:
        print("[FAIL] Results differ between old and new logic!")
    
    print("\nNote: The daily_ma and daily_rolling_max logic needs additional NaN checks.")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
