#!/usr/bin/env python3
"""
JSON parsing helpers for Takeout metadata.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def get_true_filename_from_json(json_path: str) -> str | None:
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f).get('title')
    except (json.JSONDecodeError, IOError, KeyError):
        return None


def get_timestamp_from_json(json_path: str) -> int | None:
    """Try photoTakenTime first, fall back to creationTime."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        timestamp = data.get("photoTakenTime", {}).get("timestamp")
        if not timestamp:
            timestamp = data.get("creationTime", {}).get("timestamp")
        if not timestamp:
            return None

        timestamp_int = int(timestamp)

        # Sanity check: reasonable date range for photos (1970-2030)
        # Unix epoch 0 = 1970-01-01, 1893456000 = 2030-01-01
        min_timestamp = 0  # 1970-01-01
        max_timestamp = 1893456000  # 2030-01-01

        if timestamp_int < min_timestamp:
            print(
                f"WARNING: Timestamp before 1970 in '{os.path.basename(json_path)}': "
                f"{timestamp_int} (date: {datetime.fromtimestamp(timestamp_int, timezone.utc)})"
            )
        elif timestamp_int > max_timestamp:
            date_str = datetime.fromtimestamp(timestamp_int, timezone.utc).strftime("%Y-%m-%d")
            print(
                f"WARNING: Timestamp after 2030 in '{os.path.basename(json_path)}': "
                f"{timestamp_int} (date: {date_str})"
            )

        return timestamp_int
    except (json.JSONDecodeError, IOError, ValueError, TypeError):
        return None


def get_valid_gps_from_supplemental(json_path: str):
    """Extract valid GPS coordinates from supplemental JSON.
    Returns (latitude, longitude, altitude) or None if invalid.
    Priority: geoDataExif > geoData
    Only returns if coordinates are valid (not Null Island at 0,0).
    Note: (0, lon) or (lat, 0) are VALID - only (0, 0) is invalid.
    Handles both numeric and string GPS values (converts strings to float).
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Try geoDataExif first (more accurate, from original EXIF)
        geo_exif = data.get('geoDataExif', {})
        if geo_exif:
            try:
                lat = float(geo_exif.get('latitude', 0))
                lon = float(geo_exif.get('longitude', 0))
                alt = float(geo_exif.get('altitude', 0))

                # Invalid only if BOTH lat AND lon are 0 (Null Island)
                # Points on equator (lat=0) or prime meridian (lon=0) are valid
                if not (abs(lat) < 0.0001 and abs(lon) < 0.0001):
                    return (lat, lon, alt)
            except (ValueError, TypeError):
                # Conversion failed, fall through to try geoData
                pass

        # Fallback to geoData
        geo_data = data.get('geoData', {})
        if geo_data:
            try:
                lat = float(geo_data.get('latitude', 0))
                lon = float(geo_data.get('longitude', 0))
                alt = float(geo_data.get('altitude', 0))

                # Invalid only if BOTH lat AND lon are 0 (Null Island)
                if not (abs(lat) < 0.0001 and abs(lon) < 0.0001):
                    return (lat, lon, alt)
            except (ValueError, TypeError):
                # Conversion failed
                pass

        # No valid GPS found
        return None
    except Exception:
        return None
