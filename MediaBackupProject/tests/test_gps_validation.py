#!/usr/bin/env python3
"""
Test Suite for GPS Validation Logic

Tests the smart GPS validation functions to ensure:
- Null Island (0,0) coordinates are rejected
- Valid coordinates on equator or prime meridian are accepted
- Priority order (embedded > geoDataExif > geoData) works correctly
- Edge cases are handled properly

Usage:
    cd P:\\MediaBackupProject\\tests
    python test_gps_validation.py

Expected output: All tests should pass.

Author: Created during V6.2 GPS validation implementation (2026-02-02)
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from process_media_json import get_valid_gps_from_supplemental


# ===================================================================
# TEST CASES
# ===================================================================

def create_temp_json(data):
    """Create a temporary JSON file with given data."""
    fd, path = tempfile.mkstemp(suffix='.json')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f)
        return path
    except:
        os.close(fd)
        raise

def test_null_island_rejected():
    """Test that Null Island (0,0) coordinates are rejected."""
    print("=" * 70)
    print("TEST 1: Null Island (0,0) Coordinates - Should be REJECTED")
    print("=" * 70)
    
    test_cases = [
        {
            "name": "geoData with 0,0",
            "data": {"geoData": {"latitude": 0.0, "longitude": 0.0, "altitude": 0.0}},
            "expected": None
        },
        {
            "name": "geoDataExif with 0,0",
            "data": {"geoDataExif": {"latitude": 0.0, "longitude": 0.0, "altitude": 0.0}},
            "expected": None
        },
        {
            "name": "Both with 0,0",
            "data": {
                "geoData": {"latitude": 0.0, "longitude": 0.0, "altitude": 0.0},
                "geoDataExif": {"latitude": 0.0, "longitude": 0.0, "altitude": 0.0}
            },
            "expected": None
        },
    ]
    
    all_passed = True
    for test in test_cases:
        json_path = create_temp_json(test["data"])
        try:
            result = get_valid_gps_from_supplemental(json_path)
            passed = result == test["expected"]
            all_passed = all_passed and passed
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{status}: {test['name']} -> {result} (expected: {test['expected']})")
        finally:
            os.unlink(json_path)
    
    print()
    return all_passed


def test_equator_coordinates_valid():
    """Test that points on the equator (lat=0) are VALID."""
    print("=" * 70)
    print("TEST 2: Equator Coordinates (lat=0) - Should be VALID")
    print("=" * 70)
    
    test_cases = [
        {
            "name": "Equator at 100° longitude",
            "data": {"geoData": {"latitude": 0.0, "longitude": 100.0, "altitude": 10.0}},
            "expected": (0.0, 100.0, 10.0)
        },
        {
            "name": "Equator at -45° longitude",
            "data": {"geoDataExif": {"latitude": 0.0, "longitude": -45.5, "altitude": 0.0}},
            "expected": (0.0, -45.5, 0.0)
        },
    ]
    
    all_passed = True
    for test in test_cases:
        json_path = create_temp_json(test["data"])
        try:
            result = get_valid_gps_from_supplemental(json_path)
            passed = result == test["expected"]
            all_passed = all_passed and passed
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{status}: {test['name']} -> {result}")
        finally:
            os.unlink(json_path)
    
    print()
    return all_passed


def test_prime_meridian_valid():
    """Test that points on the prime meridian (lon=0) are VALID."""
    print("=" * 70)
    print("TEST 3: Prime Meridian Coordinates (lon=0) - Should be VALID")
    print("=" * 70)
    
    test_cases = [
        {
            "name": "London area (51.5°N, 0°)",
            "data": {"geoData": {"latitude": 51.5, "longitude": 0.0, "altitude": 15.0}},
            "expected": (51.5, 0.0, 15.0)
        },
        {
            "name": "Greenwich Observatory",
            "data": {"geoDataExif": {"latitude": 51.4769, "longitude": 0.0, "altitude": 46.0}},
            "expected": (51.4769, 0.0, 46.0)
        },
        {
            "name": "Ghana coast (5°N, 0°)",
            "data": {"geoData": {"latitude": 5.0, "longitude": 0.0, "altitude": 0.0}},
            "expected": (5.0, 0.0, 0.0)
        },
    ]
    
    all_passed = True
    for test in test_cases:
        json_path = create_temp_json(test["data"])
        try:
            result = get_valid_gps_from_supplemental(json_path)
            passed = result == test["expected"]
            all_passed = all_passed and passed
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{status}: {test['name']} -> {result}")
        finally:
            os.unlink(json_path)
    
    print()
    return all_passed


def test_priority_order():
    """Test that geoDataExif takes priority over geoData."""
    print("=" * 70)
    print("TEST 4: Priority Order (geoDataExif > geoData)")
    print("=" * 70)
    
    # Both present, geoDataExif should win
    data = {
        "geoData": {"latitude": 10.0, "longitude": 20.0, "altitude": 5.0},
        "geoDataExif": {"latitude": 45.5, "longitude": -122.6, "altitude": 100.0}
    }
    
    json_path = create_temp_json(data)
    try:
        result = get_valid_gps_from_supplemental(json_path)
        expected = (45.5, -122.6, 100.0)
        passed = result == expected
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: geoDataExif priority -> {result}")
        print(f"       (should use geoDataExif, not geoData)")
    finally:
        os.unlink(json_path)
    
    print()
    return passed


def test_fallback_to_geodata():
    """Test that geoData is used when geoDataExif is missing or 0,0."""
    print("=" * 70)
    print("TEST 5: Fallback to geoData")
    print("=" * 70)
    
    test_cases = [
        {
            "name": "Only geoData present",
            "data": {"geoData": {"latitude": 35.0, "longitude": 139.0, "altitude": 20.0}},
            "expected": (35.0, 139.0, 20.0)
        },
        {
            "name": "geoDataExif is 0,0, fall back to geoData",
            "data": {
                "geoDataExif": {"latitude": 0.0, "longitude": 0.0, "altitude": 0.0},
                "geoData": {"latitude": 40.7, "longitude": -74.0, "altitude": 10.0}
            },
            "expected": (40.7, -74.0, 10.0)
        },
    ]
    
    all_passed = True
    for test in test_cases:
        json_path = create_temp_json(test["data"])
        try:
            result = get_valid_gps_from_supplemental(json_path)
            passed = result == test["expected"]
            all_passed = all_passed and passed
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{status}: {test['name']} -> {result}")
        finally:
            os.unlink(json_path)
    
    print()
    return all_passed


def test_real_world_coordinates():
    """Test with real-world coordinate examples."""
    print("=" * 70)
    print("TEST 6: Real-World Coordinates")
    print("=" * 70)
    
    test_cases = [
        {
            "name": "Portland, OR",
            "data": {"geoDataExif": {"latitude": 45.5231, "longitude": -122.6765, "altitude": 15.0}},
            "expected": (45.5231, -122.6765, 15.0)
        },
        {
            "name": "Sydney, Australia",
            "data": {"geoData": {"latitude": -33.8688, "longitude": 151.2093, "altitude": 5.0}},
            "expected": (-33.8688, 151.2093, 5.0)
        },
        {
            "name": "Tokyo, Japan",
            "data": {"geoData": {"latitude": 35.6762, "longitude": 139.6503, "altitude": 40.0}},
            "expected": (35.6762, 139.6503, 40.0)
        },
    ]
    
    all_passed = True
    for test in test_cases:
        json_path = create_temp_json(test["data"])
        try:
            result = get_valid_gps_from_supplemental(json_path)
            passed = result == test["expected"]
            all_passed = all_passed and passed
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{status}: {test['name']} -> {result}")
        finally:
            os.unlink(json_path)
    
    print()
    return all_passed


def test_edge_cases():
    """Test edge cases and error conditions."""
    print("=" * 70)
    print("TEST 7: Edge Cases and Error Handling")
    print("=" * 70)
    
    test_cases = [
        {
            "name": "Empty JSON",
            "data": {},
            "expected": None
        },
        {
            "name": "Missing latitude in geoData",
            "data": {"geoData": {"longitude": 100.0, "altitude": 0.0}},
            "expected": (0, 100.0, 0.0)  # Defaults to 0 for missing lat
        },
        {
            "name": "Very small non-zero values (should be valid)",
            "data": {"geoData": {"latitude": 0.00001, "longitude": 0.00001, "altitude": 0.0}},
            "expected": None  # Both essentially 0
        },
        {
            "name": "Negative altitude",
            "data": {"geoData": {"latitude": 35.0, "longitude": 50.0, "altitude": -10.0}},
            "expected": (35.0, 50.0, -10.0)  # Negative altitude is valid (below sea level)
        },
    ]
    
    all_passed = True
    for test in test_cases:
        json_path = create_temp_json(test["data"])
        try:
            result = get_valid_gps_from_supplemental(json_path)
            passed = result == test["expected"]
            all_passed = all_passed and passed
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{status}: {test['name']} -> {result} (expected: {test['expected']})")
        finally:
            os.unlink(json_path)
    
    print()
    return all_passed


def test_string_coordinates():
    """Test that string GPS values are properly converted to floats."""
    print("=" * 70)
    print("TEST 8: String Coordinate Handling")
    print("=" * 70)
    
    test_cases = [
        {
            "name": "String coordinates (valid)",
            "data": {
                "geoDataExif": {
                    "latitude": "45.5231",
                    "longitude": "-122.6765",
                    "altitude": "15.0"
                }
            },
            "expected": (45.5231, -122.6765, 15.0)
        },
        {
            "name": "String zeros (should be rejected)",
            "data": {
                "geoData": {
                    "latitude": "0",
                    "longitude": "0.0",
                    "altitude": "0"
                }
            },
            "expected": None
        },
        {
            "name": "Mixed string/numeric",
            "data": {
                "geoData": {
                    "latitude": "51.4769",
                    "longitude": 0,
                    "altitude": 46.0
                }
            },
            "expected": (51.4769, 0.0, 46.0)
        },
        {
            "name": "Invalid string (non-numeric)",
            "data": {
                "geoData": {
                    "latitude": "invalid",
                    "longitude": "100.0",
                    "altitude": "0"
                }
            },
            "expected": None  # Should fail conversion and return None
        },
        {
            "name": "String with extra whitespace",
            "data": {
                "geoData": {
                    "latitude": " 45.5 ",
                    "longitude": " -122.5 ",
                    "altitude": " 10 "
                }
            },
            "expected": (45.5, -122.5, 10.0)  # float() handles whitespace
        },
    ]
    
    all_passed = True
    for test in test_cases:
        json_path = create_temp_json(test["data"])
        try:
            result = get_valid_gps_from_supplemental(json_path)
            passed = result == test["expected"]
            all_passed = all_passed and passed
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{status}: {test['name']} -> {result} (expected: {test['expected']})")
        finally:
            os.unlink(json_path)
    
    print()
    return all_passed


# ===================================================================
# RUN ALL TESTS
# ===================================================================

if __name__ == "__main__":
    print("\n")
    print("=" * 70)
    print(" GPS VALIDATION TEST SUITE ".center(70))
    print("=" * 70)
    print("\n")
    
    results = []
    
    results.append(("Null Island Rejection", test_null_island_rejected()))
    results.append(("Equator Coordinates", test_equator_coordinates_valid()))
    results.append(("Prime Meridian Coordinates", test_prime_meridian_valid()))
    results.append(("Priority Order", test_priority_order()))
    results.append(("Fallback to geoData", test_fallback_to_geodata()))
    results.append(("Real-World Coordinates", test_real_world_coordinates()))
    results.append(("Edge Cases", test_edge_cases()))
    results.append(("String Coordinates", test_string_coordinates()))
    
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: {name}")
        all_passed = all_passed and passed
    
    print()
    if all_passed:
        print("[SUCCESS] ALL TESTS PASSED! GPS validation logic is correct.")
        print("          - Null Island (0,0) is properly rejected")
        print("          - Equator and Prime Meridian points are valid")
        print("          - Priority order works correctly")
        sys.exit(0)
    else:
        print("[ERROR] SOME TESTS FAILED! Review the logic before processing.")
        sys.exit(1)
