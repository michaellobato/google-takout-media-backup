# Google Photos Backup & Organization Project

## ⚠️ CRITICAL IMMUTABILITY RULE ⚠️

**`/takeout-archives/` IS SACRED AND IMMUTABLE.**

- **NEVER move files from this directory**
- **NEVER modify files in this directory**
- **NEVER delete files from this directory**
- **ONLY read, copy, or extract from this directory**

This allows you to nuke the entire project and start over at any time without re-downloading from Google. All scripts are designed to respect this rule. If any script violates this, it is a critical bug.

---

## 1. Primary Goal
The primary goal is to create a **safe, complete, and accurate backup of all media** from a Google Takeout export, with as much metadata preserved as is technically feasible. This will allow for the confident cleanup of Google Cloud storage. A critical sub-task is correcting the `Date Taken` for all media to ensure the backup is chronologically accurate and usable in photo management software.

## 2. Project Directory Structure
-   `/takeout-archives/`: **[IMMUTABLE]** Contains all original `.zip` and standalone media files from Google. Nothing is ever moved or modified here.
-   `/completed-archives/`: Reserved for future use. (Archives are currently tracked via `.processed_archives_pass2.log`.)
-   `/corrupt-archives/`: **[DEPRECATED - NO LONGER USED]** Corrupt archives are now logged in `.corrupt_archives.log` but remain in `/takeout-archives/` per the immutability rule.
-   `/json-repository/`: A centralized, flat repository of all `.json` metadata files extracted from all archives (including supplemental metadata).
-   `/json-conflicts/`: Any `.json` files that have the same name but different content are quarantined here for manual review.
-   `/workbench/`: A temporary working directory where a single archive is extracted and processed at a time.
-   `/tools/`: Contains the `exiftool` (`exiftool-13.48_64/exiftool.exe`).
-   `/scripts/`: Contains the Python scripts and Pass 2 helper modules (`process_media_*.py`).
-   `/tests/`: Contains test scripts (unit + integration-lite).
-   `/test_data/`: Contains test fixtures and sample data for validating scripts (JSON samples, media samples). See `test_data/README.md` for details.

## 3. Key Takeout Format Challenges
Our investigation revealed several critical complexities with the Google Takeout format that the scripts are designed to handle:
-   **Scattered Metadata:** A photo and its `.json` file are not guaranteed to be in the same `.zip` archive. Google optimizes archives for ~2GB size, not logical grouping. We confirmed that primary JSON and supplemental metadata files are often split across different archives from their media files, necessitating the two-pass strategy.
-   **File Name Truncation:** Google truncates long filenames on disk (to 47 characters for the filename portion, excluding extension), but the full name is preserved in the JSON `title` field. For example, `a5025662-cb40-45dd-be98-684ee48aa226_IMG_20210818_122959697_HDR.jpg` becomes `a5025662-cb40-45dd-be98-684ee48aa226_IMG_202108.jpg` on disk.
-   **Edited Photos:** Edited files (`photo-edited.jpg`) are often included alongside originals (`photo.jpg`), with both linking to a single JSON.
-   **Character Substitution:** Characters like `&` and `?` in a JSON title are replaced with `_` in the actual filename.
-   **Extension Mismatch:** A JSON may specify `.jpeg` while the file on disk is `.jpg`, and vice-versa.
-   **Duplicate File Names:** When you have multiple different files with the same name (e.g., camera counter resets), Google adds suffixes like `(0)`, `(1)`, `(2)` before the extension. The corresponding supplemental metadata files use the same suffix pattern: `IMG_3136.MOV.supplemental-metadata(1).json` for `IMG_3136(1).MOV`.
-   **Supplemental Metadata:** Google generates extra metadata files (`...supplemental-metadata.json`) containing useful data like GPS coordinates and timestamps. Some archives also include `.sup.json` shorthand files; the script treats those as supplemental too. These often exist even when primary JSON is missing and are critical for metadata recovery.

**Note:** Many of these challenges were also documented by the community, particularly in [TakeoutExtractor](https://github.com/andyjohnson0/TakeoutExtractor) which helped inform our implementation.

## 4. Final Workflow: The Two-Pass Strategy

### Pass 1: Consolidate All Metadata
-   **Script:** `1-extract-json.py`
-   **Purpose:** To create a complete and accurate index of all metadata *before* processing any large media files.
-   **Process:** The script iterates through all archives in `/takeout-archives/` (READ-ONLY). It maintains a log (`.processed_archives.log`) to instantly skip already-processed archives on re-runs. For each new archive, it extracts all `.json` files (including supplemental metadata) into the `/json-repository/`, intelligently handling corrupt archives (logged but left in place) and metadata conflicts.

### Pass 2: Process Media Archives
-   **Script:** `2-process-media.py`
-   **Purpose:** To safely process media from **zip archives only** (standalone files are handled manually), using the central JSON repository as a map.
-   **Immutability Enforcement:** All files under `/takeout-archives/` are COPIED (never moved). Files in `/workbench/` (extracted copies) are moved to final destinations.
-   **Key Features:**
    -   **Media-Driven Matching:** It iterates media files in the workbench and generates a **small, exact set of JSON candidates** for each file. No suffix guessing or `(1..30)` expansion.
    -   **Timestamp Source Order:** Embedded EXIF → primary JSON → supplemental JSON. When JSON is used, its timestamp is explicitly written into the media file (`DateTimeOriginal`, `CreateDate`, `FileModifyDate`). Embedded video timestamps also check QuickTime tags (`MediaCreateDate`, `TrackCreateDate`, `QuickTime:CreateDate`). If none contain valid timestamp data, the file is moved to `__NEEDS_REVIEW__` for manual sorting (filesystem timestamps are NOT used as they don't represent actual photo dates).
    -   **Stateful Batching:** It uses a log file (`workbench/.processed_files.log`) to track successfully processed media files. This allows the script to be safely stopped and resumed. In Pass 2, `--batch-size` controls how many **work items** (zip archives or standalone media files) are processed per run. When running **without** `--archive-name`, the log is **cleared automatically** if you use `--force-extract` or `--clean-workbench` to avoid unbounded growth.
    -   **Archive Tracking:** It maintains `.processed_work_items_pass2.log` in the project root to skip already-processed archives and standalone files in subsequent runs.
    -   **Path Length Validation:** Before file operations, destination paths are checked against Windows 11's 260-character limit. Files with paths exceeding 240 characters (safety buffer) are moved to `__NEEDS_REVIEW__/path-too-long/` and logged in `.path_too_long_pass2.log` for manual handling.
    -   **Completion Rule:** A work item (archive or standalone file) is only marked processed after the full scan/attempt completes without a catastrophic failure. Warnings and handled errors still count as completed, and are summarized in the run output for review.
    -   **Data Integrity:** It copies the primary `.json` file alongside the media file in a per-file bundle folder (named after the media file without extension), ensuring the original metadata is never lost.
    -   **Needs Review Handling:** Files without any usable timestamp (embedded/JSON/supplemental) are moved to `__NEEDS_REVIEW__/unmatched-media/`.
    -   **Path Length Handling:** Files with destination paths exceeding Windows limits are moved to `__NEEDS_REVIEW__/path-too-long/` for manual review.

---

## 4.1 Media-Driven Pass 2 (Current)

**Goals:**
1. Process **only archives** (standalone files handled manually outside the script).
2. Iterate **media files in the workbench**, not the entire JSON repository.
3. Use strict, safe matching rules to prevent wrong metadata pairing.

**Algorithm:**
1. Extract the archive to `/workbench/`.
2. Build a JSON lookup (case-insensitive map of filename → full path).
3. Iterate each media file in the workbench (skip `.json` files).
4. Generate a **small set of exact JSON candidates** for that media file. Primary JSON candidates are `<media_name>.json` plus the suffix-after-extension variant. Supplemental candidates include `.supplemental-metadata*.json` and `.sup*.json` variants.
5. Move media + **all matched JSONs** into the destination bundle folder.
6. Embed metadata only if missing. Timestamp order is Embedded EXIF → primary JSON → any supplemental JSON. GPS order is embedded if valid → supplemental if valid.
7. If **no usable timestamp** anywhere, send to `__NEEDS_REVIEW__`.

**Matching Rules (Strict):**
1. Unsuffixed media must **not** match suffixed JSON.
2. Suffixed media must **only** match JSONs with the same suffix (any supported placement).
3. No suffix guessing or `(1..30)` range expansion.

---

## 4.2 Pass 2 Code Layout (Current)

-   `2-process-media.py`: CLI entrypoint + orchestration (thin wrapper).
-   `process_media_config.py`: Config dataclass + path builder.
-   `process_media_suffix.py`: Suffix parsing + candidate generation.
-   `process_media_json.py`: JSON parsing helpers (timestamps/GPS).
-   `process_media_matching.py`: Matching rules for JSON candidates.
-   `process_media_exif.py`: ExifTool helpers + embedded metadata reads.
-   `process_media_paths.py`: Workbench + path helpers.
-   `process_media_logs.py`: Progress + issue logs.
-   `process_media_indexing.py`: Media indexing/lookup helpers.
-   `process_media_json_lookup.py`: JSON lookup + supplemental index helpers.
-   `process_media_workflow.py`: Work item selection + media processing helpers.
-   `process_media_recovery.py`: Fallback recovery helpers.
-   `process_media_status.py`: Status report rendering.

---

## 5. CURRENT PROJECT STATUS (as of 2026-02-02)

1.  **Pass 1 Status: COMPLETE.** The `1-extract-json.py` script has been run on all archives. The `/json-repository` is fully populated.
2.  **Investigation Results:**
    -   **Corrupt Archives:** Any corrupt archives are logged in `.corrupt_archives.log` and remain in `/takeout-archives/` per the immutability rule. They can be manually re-downloaded and replaced if needed.
    -   **JSON Conflicts:** A large number of conflicts were found. Manual investigation confirmed that **no primary metadata files** were in conflict. All quarantined files are non-essential `supplemental-metadata.json` files.
3.  **Tooling Status:** The scripts `1-extract-json.py` (V3) and `2-process-media.py` (V6.2) are feature-complete for the current workflow, including fallback metadata handling, per-file bundle folders, optimized performance via media file indexing, smart suffix detection, and intelligent GPS validation.
4.  **Production Status:** Live processing is active and working correctly. 2 archives have been successfully processed (90 media files organized to Z: drive). Continuing with small batch sizes for controlled progress monitoring. **Do NOT reset logs** - they track your progress and allow safe resumption.

## 6. Recent Improvements (V6, V6.1, V6.2 - 2026-02-02)
1.  **EXIF Regex Fix:** Corrected regex pattern in `get_exif_datetime()` to properly extract EXIF timestamps.
2.  **UTC Timestamp Handling:** All Google Takeout timestamps now properly interpreted as UTC to prevent timezone-related date errors. Updated to use timezone-aware datetime objects (`datetime.fromtimestamp(timestamp, timezone.utc)`) to eliminate deprecation warnings and ensure Python 3.12+ compatibility.
3.  **Performance Optimization:** Implemented media file indexing to eliminate O(n³) complexity. The script now builds a single index at startup instead of walking directories 72,000+ times.
4.  **Progress Indicators:** Added progress logging every 10,000 JSONs and every 10,000 media files indexed (reduced noise while maintaining visibility).
5.  **Removed Filesystem Timestamp Fallback:** Filesystem timestamps (ctime/mtime) don't represent when photos were actually taken, so they're no longer used as a fallback. Files without real metadata go directly to `__NEEDS_REVIEW__`.
6.  **Windows Path Length Validation:** Added checks for Windows 11's 260-character path limit. Files that would exceed the limit are automatically moved to `__NEEDS_REVIEW__/path-too-long/` with their metadata for manual handling.
7.  **Status Report Command:** Added `--status` flag to display comprehensive progress report and issue summary across all log files. Essential for multi-day processing sessions.
8.  **ExifTool Failure Logging:** All ExifTool metadata merge failures are now logged to `.exiftool_failures_pass2.log` with context (primary JSON, supplemental, orphan recovery). Files are still processed, but warnings help identify systemic issues.
9.  **Google Suffix Handling:** Fixed critical bug in supplemental metadata matching to handle Google's duplicate file naming pattern. When Google has multiple files with the same name (e.g., from camera counter resets), it adds suffixes like `(0)`, `(1)`, `(2)`, etc. The script now correctly matches `IMG_3136(1).MOV` with `IMG_3136.MOV.supplemental-metadata(1).json` using regex pattern matching for any numeric suffix. ALL supplemental metadata files are now copied (not just one), preserving complete metadata even when Google creates multiple versions.
10. **Strict Suffix Matching:** Suffixes are matched exactly when present. The script does **not** guess or expand `(1..30)` ranges. This prevents accidental cross-matching between unsuffixed and suffixed files.
11. **Timestamp Validation:** Added sanity checks for JSON timestamps to detect corrupted or invalid dates. Timestamps outside the range 1970-2030 trigger console warnings for manual review while still processing the files normally.
12. **Enhanced Error Logging:** Exception handling now includes full stack traces and contextual information (JSON filename, destination path) to aid in debugging issues during processing.
13. **Smart GPS Validation (V6.2):** GPS coordinates are now validated before embedding to prevent "Null Island" (0,0) coordinates from being written to files. Priority order: preserves existing embedded GPS if valid, tries `geoDataExif` from supplemental metadata first (more accurate), then falls back to `geoData`, and skips GPS embedding entirely if all sources are null or 0,0. This ensures only legitimate location data enriches your photos.

## 7. Edge Cases & Decisions (Current)
1.  **Immutability Enforcement:** All file operations check source location. Files from `/takeout-archives/` are ALWAYS copied. Files from `/workbench/` (extracted temp files) are moved. This is checked programmatically using `is_under_dir()` before every move operation.
2.  **No Primary JSON:** A file may have no primary JSON but still contain embedded EXIF (HEIC/JPG often do). Embedded EXIF is treated as the first-choice timestamp source.
3.  **Supplemental Metadata:** Supplemental JSON often contains useful timestamps/geo. ALL matching supplemental metadata files are copied alongside media (not just one). This handles Google's duplicate file naming where `IMG_3136(0).MOV` and `IMG_3136(1).MOV` are different files with different metadata. Supplemental can be used as fallback if embedded and primary JSON timestamps are missing.
4.  **Google Duplicate Suffixes:** When multiple files have the same base name (e.g., camera counter reset), Google adds `(0)`, `(1)`, `(2)` etc. The script treats suffixes of **1–3 digits** as duplicates and matches them strictly.
5.  **Fallback Order:** Embedded EXIF → primary JSON → supplemental JSON → `__NEEDS_REVIEW__` (filesystem timestamps are NOT used).
6.  **Standalone Files:** Standalone files are **excluded** from Pass 2 and should be handled manually outside the script.
7.  **No Orphan Sweep:** Media files are processed directly from the workbench. If no usable timestamp exists, the file is sent to `__NEEDS_REVIEW__`.
8.  **Bundle Folders:** Final output uses per-file bundle folders: `...\YYYY\MM\<BaseName>\` containing media + all metadata copies.
9.  **Destination Collisions:** If a destination media file already exists, the script skips moving the media, copies any matched JSONs into the bundle folder, and marks the source as processed to avoid repeated attempts.
10. **Audit Logs:** `.processed_work_items_pass2.log`, `.path_too_long_pass2.log`, `.exiftool_failures_pass2.log`, `.corrupt_archives.log` track progress and exceptions. Use `--status` flag to see a summary.

---

## 8. Testing & Validation

### Run All Tests (Recommended)
```powershell
cd P:\MediaBackupProject\tests
python test_all.py
```

Runs every test script in the `tests/` folder, including integration-lite IO tests that use temporary files and ExifTool. Any `[FAIL]` means stop and investigate. `[WARN]` flags known gaps that are currently informational.


### Test Suites

**Suffix Detection Tests:**
```powershell
cd P:\MediaBackupProject\tests
python test_suffix_logic.py
```

Validates:
- **Strict Suffix Extraction:** Only 1–3 digit suffixes are treated as Google duplicates; year-like `(2020)` is ignored
- **Strict Candidate Generation:** Unsuffixed media must not match suffixed JSON, and suffixed media matches only the same suffix
- **Supplemental Variants:** `.supplemental-metadata` and `.sup` patterns (before/after extension)
- **Real-World Scenarios:** Tests actual patterns observed in your data (e.g., `MOVIE.mp4(26).json`)

**GPS Validation Tests:**
```powershell
cd P:\MediaBackupProject\tests
python test_gps_validation.py
```

Validates:
- **Null Island Rejection:** Ensures (0,0) coordinates are NOT embedded
- **Equator & Prime Meridian:** Confirms points at (0, lon) or (lat, 0) are VALID
- **Priority Order:** Verifies geoDataExif takes precedence over geoData
- **Fallback Logic:** Tests fallback when geoDataExif is missing or invalid
- **Real-World Coordinates:** Validates actual location data (Portland, Sydney, Tokyo)
- **Edge Cases:** Empty JSON, missing fields, negative altitude, etc.

**Integration Tests:**
```powershell
cd P:\MediaBackupProject\tests
python test_integration.py
```

Validates the entire GPS validation pipeline using real Google Takeout JSON files from the `test_data/` folder:
- **Real Valid GPS:** Tests actual supplemental metadata with Portland coordinates
- **Real Null Island:** Tests actual file with (0,0) coordinates (should be rejected)
- **Synthetic Edge Cases:** Equator and Prime Meridian points
- **Priority Verification:** Ensures geoDataExif beats geoData with real JSON structure

**Media IO Tests (Integration-lite):**
```powershell
cd P:\MediaBackupProject\tests
python test_media_io.py
```

Validates core file-handling behaviors using temporary files:
- **Supplemental Matching:** Matching logic for suffix and non-suffix cases
- **Extension Normalization:** ExifTool-driven file extension correction
  - **Embedded GPS:** Valid vs 0,0 detection (near-zero treated as invalid)
- **Path Length Validation:** Edge cases around MAX_PATH_LENGTH

**JSON + Timestamp Tests:**
```powershell
cd P:\MediaBackupProject\tests
python test_json_and_timestamps.py
```

Validates:
- JSON parsing for titles
- Photo timestamps (photoTakenTime/creationTime)
- Missing/invalid JSON handling

**Filename Logic Tests:**
```powershell
cd P:\MediaBackupProject\tests
python test_filename_logic.py
```

Validates:
- Title normalization with suffix placement
- Suffix extraction (media + JSON)
- Candidate generation & extension variants

**Indexing + Lookup Tests:**
```powershell
cd P:\MediaBackupProject\tests
python test_indexing_and_lookup.py
```

Validates:
- Media indexing (skips JSON, case-insensitive)
- Allowed-path filtering
- Lookup behavior with processed files

**Paths + Workbench Tests:**
```powershell
cd P:\MediaBackupProject\tests
python test_paths_and_workbench.py
```

Validates:
- Path containment checks
- Archive path resolution
- Workbench empty/non-empty detection

**Workflow Logic Tests:**
```powershell
cd P:\MediaBackupProject\tests
python test_workflow_logic.py
```

Validates core Pass 2 workflow behavior end-to-end in a temporary sandbox:
- Embedded timestamps win over JSON
- Primary JSON fallback
- Supplemental fallback
- No metadata -> `__NEEDS_REVIEW__`
- EXIF fallback (no JSON)
- Supplemental fallback (no primary)
- Path-too-long handling
- Unmatched work item logging
- Suffix matching (workflow-level)


**Expected output:** All tests should pass with `[SUCCESS] ALL TESTS PASSED!` message. If any tests fail, do not proceed with live processing.

**IDE Import Note (VSCode/Pylance):** `pyrightconfig.json` adds `scripts/` to `extraPaths` so `process_media_*` imports resolve cleanly in tests.

### Dry Run Testing
You can test the full processing pipeline without modifying any files:

```powershell
# Test on one archive without making changes most common approach
python 2-process-media.py --batch-size 1 --force-extract
```

Omit the `--live` flag to see what the script WOULD do without actually moving/copying files to `Z:`. Review the output for any warnings or unexpected behavior before running in live mode.

**Workbench behavior:** Dry runs still extract into `/workbench/`. To keep the extracted files for inspection, omit `--clean-workbench`. To reset the workbench before the next run, use `--force-extract`.

### Pass 2 CLI Quick Reference
You can always see the current flags with:
```powershell
python 2-process-media.py --help
```

**Flags:**
- `--status`: Print a status report (logs + progress) and exit.
- `--live`: Actually move files and write metadata. (Default is dry run.)
- `--batch-size N`: Limit to N work items (zip archives).
- `--archive-name <zip>`: Process a specific zip by name or full path.
- `--force-extract`: Clear `/workbench/Takeout` before extraction.
- `--clean-workbench`: Clear `/workbench/Takeout` after the run completes.

**Re-running a processed archive:** If the archive name is already in `.processed_work_items_pass2.log`, the script will refuse to re-run it unless you either remove the log entry or use `--archive-name <zip> --force-extract` (force-extract bypasses the processed check).

---

## 9. Monitoring Progress & Status

### Status Report Command
At any time, you can check the overall progress and identify issues by running:
```powershell
cd P:\MediaBackupProject\scripts
python 2-process-media.py --status
```

This displays:
- **Progress:** How many archives/files have been processed (e.g., "Archives processed: 145 / 611")
- **Issues:** Summary of all problems with severity indicators:
  - `[ERROR]` - Critical issues requiring immediate attention
  - `[WARN]` - Non-critical issues to review later
  - `[INFO]` - Informational notices
  - `[OK]` - No issues found
- **Log Locations:** Where to find detailed logs for investigation

**Use this when:**
- Resuming work after days/weeks
- Checking if any patterns emerged across multiple batches
- Deciding if issues are systemic (1000 failures = investigate) or edge cases (5 failures = probably fine)

### Understanding the Logs
The project maintains multiple log files for different purposes:

**Progress Logs** (for resuming after interruption):
- `.processed_work_items_pass2.log` - Archives and standalone files completed
- `workbench/.processed_files.log` - Individual media files processed (auto-cleared when running without `--archive-name` and using `--force-extract` or `--clean-workbench`)

**Issue Logs** (for manual review):
- `.exiftool_failures_pass2.log` - Files where metadata embedding failed (files are still processed, but EXIF wasn't written)
- `.path_too_long_pass2.log` - Files with paths exceeding Windows 260-char limit
- `.corrupt_archives.log` - Corrupt ZIP archives that couldn't be opened

All issue logs use simple text format: one entry per line, pipe-separated fields for easy grep/parsing.

---

## 10. NEXT STEP: How to Resume

The project is in **active production mode**. Live runs are successfully processing archives and organizing media to the Z: drive. Continue processing archives in small batches to maintain control and monitor progress.

**To resume, follow these steps:**

1.  **Check Status:** See where you left off and if any issues need attention.
    ```powershell
    cd P:\MediaBackupProject\scripts
    python 2-process-media.py --status
    ```

2.  **Run Next Batch:** Continue processing archives in live mode. Start with small batch sizes (1-5) until you're confident, then increase as desired.
    ```powershell
    python 2-process-media.py --batch-size 1 --live
    ```

3.  **Monitor Output:** Check for any warnings or errors. Review the `__NEEDS_REVIEW__` folder periodically for files that need manual attention.

4.  **Scale Up:** Once comfortable with the process, you can increase batch size to process multiple archives per run (e.g., `--batch-size 10` or `--batch-size 50`).
