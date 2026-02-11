#!/usr/bin/env python3
"""
Integration Tests Using Real Test Data

Tests the GPS validation and other logic using actual test fixtures
from the test_data folder. This ensures the code works with real
Google Takeout data structures.

Usage:
    cd P:\\MediaBackupProject\\tests
    python test_integration.py

Expected output: All tests should pass.

Author: Created during V6.2 testing (2026-02-02)
"""

import os
import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from process_media_json import get_valid_gps_from_supplemental

# Path to test data
TEST_DATA_DIR = os.path.join(ROOT_DIR, "test_data", "json_samples")


def test_real_valid_gps():
    """Test with real supplemental metadata that has valid GPS."""
    print("=" * 70)
    print("INTEGRATION TEST 1: Real Valid GPS Data (Portland, OR)")
    print("=" * 70)
    
    json_path = os.path.join(TEST_DATA_DIR, "sample_valid_gps_with_exif.json")
    
    if not os.path.exists(json_path):
        print(f"[SKIP] Test file not found: {json_path}")
        return True
    
    result = get_valid_gps_from_supplemental(json_path)
    
    # Should return Portland coordinates from geoDataExif
    expected_lat = 45.569666700000006
    expected_lon = -122.67413889999999
    
    if result:
        lat, lon, alt = result
        lat_match = abs(lat - expected_lat) < 0.001
        lon_match = abs(lon - expected_lon) < 0.001
        passed = lat_match and lon_match
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: Extracted GPS: ({lat}, {lon}, {alt})")
        print(f"       Expected: ({expected_lat}, {expected_lon}, *)")
        return passed
    else:
        print(f"[FAIL]: Returned None (expected valid GPS)")
        return False


def test_real_null_island():
    """Test with real supplemental metadata that has 0,0 coordinates."""
    print("=" * 70)
    print("INTEGRATION TEST 2: Real Null Island Data (0,0)")
    print("=" * 70)
    
    json_path = os.path.join(TEST_DATA_DIR, "sample_null_island_0_0.json")
    
    if not os.path.exists(json_path):
        print(f"[SKIP] Test file not found: {json_path}")
        return True
    
    result = get_valid_gps_from_supplemental(json_path)
    
    passed = result is None
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status}: Returned {result} (expected None for 0,0)")
    
    return passed


def test_synthetic_equator():
    """Test with synthetic equator point."""
    print("=" * 70)
    print("INTEGRATION TEST 3: Synthetic Equator Point (0, 78.4677)")
    print("=" * 70)
    
    json_path = os.path.join(TEST_DATA_DIR, "sample_equator_point.json")
    
    if not os.path.exists(json_path):
        print(f"[SKIP] Test file not found: {json_path}")
        return True
    
    result = get_valid_gps_from_supplemental(json_path)
    expected = (0.0, 78.4677, 2810.0)
    
    passed = result == expected
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status}: Extracted GPS: {result}")
    print(f"       Expected: {expected}")
    
    return passed


def test_synthetic_prime_meridian():
    """Test with synthetic prime meridian point."""
    print("=" * 70)
    print("INTEGRATION TEST 4: Synthetic Prime Meridian (51.4769, 0)")
    print("=" * 70)
    
    json_path = os.path.join(TEST_DATA_DIR, "sample_prime_meridian.json")
    
    if not os.path.exists(json_path):
        print(f"[SKIP] Test file not found: {json_path}")
        return True
    
    result = get_valid_gps_from_supplemental(json_path)
    expected = (51.4769, 0.0, 46.0)
    
    passed = result == expected
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status}: Extracted GPS: {result}")
    print(f"       Expected: {expected}")
    
    return passed


def test_priority_order():
    """Test that geoDataExif takes priority over geoData."""
    print("=" * 70)
    print("INTEGRATION TEST 5: Priority Order (geoDataExif > geoData)")
    print("=" * 70)
    
    json_path = os.path.join(TEST_DATA_DIR, "sample_priority_test.json")
    
    if not os.path.exists(json_path):
        print(f"[SKIP] Test file not found: {json_path}")
        return True
    
    result = get_valid_gps_from_supplemental(json_path)
    # Should return Portland coordinates from geoDataExif, NOT the (10, 20) from geoData
    expected = (45.5231, -122.6765, 15.0)
    
    passed = result == expected
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status}: Extracted GPS: {result}")
    print(f"       Expected: {expected} (from geoDataExif)")
    if not passed and result:
        print(f"       Note: If result is (10.0, 20.0, 5.0), geoData was used (WRONG)")
    
    return passed


# ===================================================================
# RUN ALL INTEGRATION TESTS
# ===================================================================

if __name__ == "__main__":
    print("\n")
    print("=" * 70)
    print(" INTEGRATION TEST SUITE ".center(70))
    print(" (Using Real Test Data Files) ".center(70))
    print("=" * 70)
    print("\n")
    
    results = []
    
    results.append(("Real Valid GPS", test_real_valid_gps()))
    print()
    results.append(("Real Null Island", test_real_null_island()))
    print()
    results.append(("Synthetic Equator", test_synthetic_equator()))
    print()
    results.append(("Synthetic Prime Meridian", test_synthetic_prime_meridian()))
    print()
    results.append(("Priority Order", test_priority_order()))
    print()
    
    print("=" * 70)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: {name}")
        all_passed = all_passed and passed
    
    print()
    if all_passed:
        print("[SUCCESS] ALL INTEGRATION TESTS PASSED!")
        print("          GPS validation works correctly with real data files.")
        sys.exit(0)
    else:
        print("[ERROR] SOME INTEGRATION TESTS FAILED!")
        print("        Check the GPS validation logic.")
        sys.exit(1)
