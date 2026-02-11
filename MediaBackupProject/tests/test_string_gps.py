#!/usr/bin/env python3
"""Quick test to see if string GPS coordinates break the validation."""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from process_media_json import get_valid_gps_from_supplemental

# Test with string coordinates
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
json_path = os.path.join(PROJECT_ROOT, "test_data", "json_samples", "sample_string_coordinates.json")

success = True
try:
    result = get_valid_gps_from_supplemental(json_path)
    print(f"Result: {result}")
    if result:
        lat, lon, alt = result
        print(f"Latitude: {lat} (type: {type(lat).__name__})")
        print(f"Longitude: {lon} (type: {type(lon).__name__})")
        print(f"Altitude: {alt} (type: {type(alt).__name__})")
        print("\n[PASS] String coordinates were handled successfully!")
    else:
        print("[FAIL] Returned None (should have extracted valid GPS)")
        success = False
except Exception as e:
    success = False
    print(f"[ERROR] Exception occurred: {e}")
    print(f"Type: {type(e).__name__}")
    import traceback
    traceback.print_exc()

raise SystemExit(0 if success else 1)
