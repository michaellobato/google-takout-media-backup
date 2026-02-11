# Test Data for MediaBackupProject

This folder contains test fixtures and sample data for validating the processing scripts.

## Directory Structure

```
test_data/
├── json_samples/          # Sample JSON metadata files
│   ├── sample_valid_gps_with_exif.json      # Real file: Portland, OR with geoDataExif
│   ├── sample_null_island_0_0.json          # Real file: Null Island (0,0) coordinates
│   ├── sample_equator_point.json            # Synthetic: Point on equator (0, 78.4677)
│   ├── sample_prime_meridian.json           # Synthetic: Greenwich Observatory (51.4769, 0)
│   └── sample_priority_test.json            # Synthetic: Both geoData and geoDataExif
├── media_samples/         # Sample media files (if available)
└── README.md             # This file
```

## JSON Samples Description

### Real Data (from actual Google Takeout)

**sample_valid_gps_with_exif.json** (`IMG_20170408_113443.jpg.supplemental-metadata.json`)
- **Source:** Real supplemental metadata from processed file
- **Location:** Portland, Oregon area (45.569666, -122.674138)
- **Has:** Both `geoData` and `geoDataExif`
- **Use:** Validates that valid GPS coordinates are properly extracted
- **Expected:** Should return (45.569666, -122.674138, 0.0) from geoDataExif

**sample_null_island_0_0.json** (`IMG_20171105_130437.jpg.supplemental-metadata.json`)
- **Source:** Real supplemental metadata from processed file
- **Location:** Null Island (0.0, 0.0) - no GPS was available
- **Has:** `geoData` with 0,0 coordinates
- **Use:** Validates that Null Island coordinates are rejected
- **Expected:** Should return None (invalid GPS)

### Synthetic Data (created for edge cases)

**sample_equator_point.json**
- **Location:** Equator in Ecuador (0.0, 78.4677, 2810m altitude)
- **Purpose:** Tests that points on the equator are VALID
- **Edge Case:** Latitude = 0, but longitude is valid
- **Expected:** Should return (0.0, 78.4677, 2810.0)

**sample_prime_meridian.json**
- **Location:** Greenwich Observatory, UK (51.4769, 0.0, 46m altitude)
- **Purpose:** Tests that points on prime meridian are VALID
- **Edge Case:** Longitude = 0, but latitude is valid
- **Has:** Both `geoData` and `geoDataExif` with same coordinates
- **Expected:** Should return (51.4769, 0.0, 46.0) from geoDataExif

**sample_priority_test.json**
- **Location (geoDataExif):** Portland, OR (45.5231, -122.6765)
- **Location (geoData):** Different location (10.0, 20.0)
- **Purpose:** Tests priority order (geoDataExif should win)
- **Expected:** Should return (45.5231, -122.6765, 15.0) from geoDataExif, NOT geoData

## Usage in Tests

The test suites can reference these files for integration testing:

```python
# Example: Load real test data
test_json_path = "P:/MediaBackupProject/test_data/json_samples/sample_valid_gps_with_exif.json"
result = get_valid_gps_from_supplemental(test_json_path)
```

## Adding New Test Data

When adding new test files:

1. **Real data:** Copy from `json-repository/` with descriptive name
2. **Synthetic data:** Create JSON with realistic structure
3. **Document here:** Add description of what it tests
4. **Name clearly:** Use `sample_<scenario>.json` pattern

## Media Samples

Currently empty. If needed, small media files (< 1MB) can be added here for integration testing of:
- EXIF extraction
- File type handling
- Metadata embedding

---

**Created:** 2026-02-02  
**Last Updated:** 2026-02-02  
**Associated Scripts:** `test_suffix_logic.py`, `test_gps_validation.py`
