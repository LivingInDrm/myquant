#coding: utf-8
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def test_series_index_equivalence():
    """Test 1: DataFrame.loc[row] returns Series with index == DataFrame.columns"""
    print("\n=== Test 1: Series Index Equivalence ===")
    
    # Create sample DataFrame
    df = pd.DataFrame({
        '000001.SZ': [1.0, 2.0, 3.0],
        '600000.SH': [4.0, 5.0, 6.0],
        '000002.SZ': [7.0, 8.0, 9.0]
    }, index=pd.date_range('2024-01-01', periods=3))
    
    print(f"DataFrame columns: {list(df.columns)}")
    
    row = df.index[0]
    series = df.loc[row]
    
    print(f"Series index: {list(series.index)}")
    print(f"Are they equal? {list(series.index) == list(df.columns)}")
    
    assert list(series.index) == list(df.columns), "FAILED: Series index != DataFrame columns"
    print("[OK] Series index equals DataFrame columns")


def test_membership_check_equivalence():
    """Test 2: `stock_code in df.columns` vs `stock_code in df.loc[row].index`"""
    print("\n=== Test 2: Membership Check Equivalence ===")
    
    df = pd.DataFrame({
        '000001.SZ': [1.0, 2.0, 3.0],
        '600000.SH': [4.0, 5.0, 6.0],
        '000002.SZ': [7.0, 8.0, 9.0]
    }, index=pd.date_range('2024-01-01', periods=3))
    
    row = df.index[0]
    series = df.loc[row]
    
    # Test existing stock
    stock_exists = '000001.SZ'
    check1 = stock_exists in df.columns
    check2 = stock_exists in series.index
    print(f"Stock '{stock_exists}' exists:")
    print(f"  in df.columns: {check1}")
    print(f"  in series.index: {check2}")
    assert check1 == check2, f"FAILED: Different results for existing stock"
    
    # Test non-existing stock
    stock_not_exists = '999999.SZ'
    check1 = stock_not_exists in df.columns
    check2 = stock_not_exists in series.index
    print(f"Stock '{stock_not_exists}' does not exist:")
    print(f"  in df.columns: {check1}")
    print(f"  in series.index: {check2}")
    assert check1 == check2, f"FAILED: Different results for non-existing stock"
    
    print("[OK] Membership checks are equivalent")


def test_value_access_equivalence():
    """Test 3: `df.loc[row, col]` vs `series = df.loc[row]; series[col]`"""
    print("\n=== Test 3: Value Access Equivalence ===")
    
    df = pd.DataFrame({
        '000001.SZ': [1.0, 2.0, 3.0],
        '600000.SH': [4.0, 5.0, 6.0],
        '000002.SZ': [np.nan, 8.0, 9.0]
    }, index=pd.date_range('2024-01-01', periods=3))
    
    row = df.index[0]
    series = df.loc[row]
    
    # Test normal value
    stock = '000001.SZ'
    val1 = df.loc[row, stock]
    val2 = series[stock]
    print(f"Stock '{stock}' value:")
    print(f"  df.loc[row, col]: {val1}")
    print(f"  series[col]: {val2}")
    assert val1 == val2, f"FAILED: Different values for normal case"
    
    # Test NaN value
    stock_nan = '000002.SZ'
    val1 = df.loc[row, stock_nan]
    val2 = series[stock_nan]
    print(f"Stock '{stock_nan}' value (NaN):")
    print(f"  df.loc[row, col]: {val1}")
    print(f"  series[col]: {val2}")
    assert (pd.isna(val1) and pd.isna(val2)) or (val1 == val2), f"FAILED: Different NaN handling"
    
    print("[OK] Value access methods are equivalent")


def test_optimization_logic_equivalence():
    """Test 4: Complete optimization logic equivalence"""
    print("\n=== Test 4: Complete Optimization Logic Equivalence ===")
    
    # Create sample momentum signals
    df = pd.DataFrame({
        '000001.SZ': [0.5, 0.3, 0.8],
        '600000.SH': [0.6, 0.7, 0.2],
        '000002.SZ': [np.nan, 0.9, 0.4],
        '600001.SH': [0.0, 0.0, 0.0]
    }, index=pd.date_range('2024-01-01', periods=3))
    
    candidates = ['000001.SZ', '600000.SH', '000002.SZ', '999999.SZ']  # 999999 doesn't exist
    
    row = df.index[1]  # 2024-01-02
    
    print(f"Testing row: {row}")
    print(f"Candidates: {candidates}")
    
    # Original logic
    original_results = []
    for stock in candidates:
        if stock in df.columns:
            signal = df.loc[row, stock]
            original_results.append((stock, signal))
        else:
            original_results.append((stock, None))
    
    # Optimized logic
    series = df.loc[row]
    optimized_results = []
    for stock in candidates:
        if stock in series.index:
            signal = series[stock]
            optimized_results.append((stock, signal))
        else:
            optimized_results.append((stock, None))
    
    print("\nOriginal results:")
    for stock, signal in original_results:
        print(f"  {stock}: {signal}")
    
    print("\nOptimized results:")
    for stock, signal in optimized_results:
        print(f"  {stock}: {signal}")
    
    # Compare results
    for (stock1, sig1), (stock2, sig2) in zip(original_results, optimized_results):
        assert stock1 == stock2, f"FAILED: Stock mismatch {stock1} vs {stock2}"
        if pd.isna(sig1) and pd.isna(sig2):
            continue
        assert sig1 == sig2, f"FAILED: Signal mismatch for {stock1}: {sig1} vs {sig2}"
    
    print("[OK] Complete logic equivalence verified")


def test_performance_comparison():
    """Test 5: Performance comparison"""
    print("\n=== Test 5: Performance Comparison ===")
    
    import time
    
    # Create large DataFrame
    num_stocks = 5000
    num_days = 250
    stocks = [f'{i:06d}.SZ' for i in range(num_stocks)]
    dates = pd.date_range('2024-01-01', periods=num_days)
    
    df = pd.DataFrame(
        np.random.rand(num_days, num_stocks),
        index=dates,
        columns=stocks
    )
    
    candidates = stocks[:100]  # Test with 100 candidates
    row = df.index[100]
    
    # Original method
    start = time.time()
    for _ in range(100):
        results1 = []
        for stock in candidates:
            if stock in df.columns:
                signal = df.loc[row, stock]
                results1.append(signal)
    time1 = time.time() - start
    
    # Optimized method
    start = time.time()
    for _ in range(100):
        series = df.loc[row]
        results2 = []
        for stock in candidates:
            if stock in series.index:
                signal = series[stock]
                results2.append(signal)
    time2 = time.time() - start
    
    print(f"DataFrame shape: {df.shape}")
    print(f"Candidates: {len(candidates)}")
    print(f"Iterations: 100")
    print(f"Original method: {time1:.4f}s")
    print(f"Optimized method: {time2:.4f}s")
    print(f"Speedup: {time1/time2:.2f}x")
    
    # Verify results are identical
    series = df.loc[row]
    for stock in candidates:
        val1 = df.loc[row, stock]
        val2 = series[stock]
        assert val1 == val2, f"FAILED: Values differ for {stock}"
    
    print("[OK] Performance test passed with identical results")


if __name__ == '__main__':
    print("=" * 60)
    print("Testing Optimization Equivalence")
    print("=" * 60)
    
    try:
        test_series_index_equivalence()
        test_membership_check_equivalence()
        test_value_access_equivalence()
        test_optimization_logic_equivalence()
        test_performance_comparison()
        
        print("\n" + "=" * 60)
        print("[OK] All tests passed!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
