# ===================================================================
# 2-process-media.py
#
# Purpose: Implements Pass 2 of the Two-Pass strategy.
#
# V6.2: GPS handling improvements (2026-02-02):
#   - Smart GPS validation: only embed if coordinates are valid (not 0,0)
#   - Priority order: embedded GPS > geoDataExif > geoData
#   - Preserves existing GPS if already valid
#   - Prevents "Null Island" (0,0) coordinates from being embedded
#
# V6.1: Code review and enhancements (2026-02-02):
#   - Smart suffix detection from JSON filenames (massive efficiency gain)
#   - Timestamp validation with sanity checks (1970-2030 range)
#   - Enhanced error logging with stack traces and context
#   - Improved documentation and code clarity
#
# V6: Optimized and refined version with performance improvements:
#   - Media file indexing for O(n) performance (no more nested walks)
#   - UTC timestamp handling for consistency
#   - EXIF regex fix for proper datetime extraction
#   - Removed filesystem timestamp fallback (only real metadata used)
#   - Progress indicators for long operations
#   - All V5 features: edge-case handling, stateful batching, data integrity
# ===================================================================

import os
import shutil
import sys
import argparse
import io
from datetime import datetime
import time

from pathlib import Path

# Ensure sibling modules in scripts/ are importable
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from process_media_config import ProcessMediaConfig, build_config
from process_media_exif import (
    get_exif_datetime,
    get_real_extension_from_exiftool,
    normalize_media_extension,
    run_exiftool,
    get_embedded_gps,
)
from process_media_json_lookup import build_json_lookup
from process_media_logs import (
    get_processed_files_log,
    get_processed_work_items,
    log_processed_work_item,
    normalize_archive_key,
)
from process_media_paths import workbench_has_files, extract_archive_to_workbench
from process_media_status import print_status_report
from process_media_workflow import (
    list_media_files,
    select_work_items,
    process_media_files,
)
# --- Configuration ---
PROJECT_ROOT = Path("P:/MediaBackupProject")
WORKBENCH_DIR = PROJECT_ROOT / "workbench"
EXTRACT_TARGET_DIR = WORKBENCH_DIR / "Takeout"
JSON_REPOSITORY_DIR = PROJECT_ROOT / "json-repository"
# CRITICAL: TAKEOUT_ARCHIVES_DIR is IMMUTABLE - never move or modify files here!
TAKEOUT_ARCHIVES_DIR = PROJECT_ROOT / "takeout-archives"
TOOLS_DIR = PROJECT_ROOT / "tools"
EXIFTOOL_DIR_BASE = TOOLS_DIR / "exiftool-13.48_64"
EXIFTOOL_DIR_EXTRA_FILES = EXIFTOOL_DIR_BASE / "exiftool_files"

# current layout:
#   P:\MediaBackupProject\tools\exiftool-13.48_64\exiftool.exe
#   P:\MediaBackupProject\tools\exiftool-13.48_64\exiftool_files\perl.exe
#   P:\MediaBackupProject\tools\exiftool-13.48_64\exiftool_files\exiftool.pl
EXIFTOOL_EXE = EXIFTOOL_DIR_BASE / "exiftool.exe"
EXIFTOOL_PERL = EXIFTOOL_DIR_EXTRA_FILES / "perl.exe"
EXIFTOOL_SCRIPT = EXIFTOOL_DIR_EXTRA_FILES / "exiftool.pl"

FINAL_LIBRARY_DIR = Path("Z:/Family Pictures and Videos")
NEEDS_REVIEW_DIR = FINAL_LIBRARY_DIR / "__NEEDS_REVIEW__"
ORPHAN_MEDIA_DIR = NEEDS_REVIEW_DIR / "unmatched-media"
PATH_TOO_LONG_DIR = NEEDS_REVIEW_DIR / "path-too-long"

# Log files for the stateful batching system.
PROCESSED_LOG_FILE = WORKBENCH_DIR / ".processed_files.log"
PROCESSED_WORK_ITEMS_LOG_FILE = PROJECT_ROOT / ".processed_work_items_pass2.log"
FALLBACK_USED_LOG_FILE = PROJECT_ROOT / ".fallback_metadata_used_pass2.log"
PROCESSED_ARCHIVES_LOG_FILE = PROJECT_ROOT / ".processed_archives_pass2.log"
PROCESSED_STANDALONE_LOG_FILE = PROJECT_ROOT / ".processed_standalone_pass2.log"
PATH_TOO_LONG_LOG_FILE = PROJECT_ROOT / ".path_too_long_pass2.log"
EXIFTOOL_FAILURES_LOG_FILE = PROJECT_ROOT / ".exiftool_failures_pass2.log"
CORRUPT_ARCHIVES_LOG_FILE = PROJECT_ROOT / ".corrupt_archives.log"

# Global config (kept in sync for backwards compatibility)
CONFIG: ProcessMediaConfig = build_config(PROJECT_ROOT, FINAL_LIBRARY_DIR)


def apply_config(cfg: ProcessMediaConfig) -> None:
    """Update module-level globals from a config (backwards compatibility)."""
    global PROJECT_ROOT, WORKBENCH_DIR, EXTRACT_TARGET_DIR, JSON_REPOSITORY_DIR
    global TAKEOUT_ARCHIVES_DIR, TOOLS_DIR, EXIFTOOL_DIR_BASE, EXIFTOOL_DIR_EXTRA_FILES
    global EXIFTOOL_EXE, EXIFTOOL_PERL, EXIFTOOL_SCRIPT
    global FINAL_LIBRARY_DIR, NEEDS_REVIEW_DIR, ORPHAN_MEDIA_DIR, PATH_TOO_LONG_DIR
    global PROCESSED_LOG_FILE, PROCESSED_WORK_ITEMS_LOG_FILE
    global FALLBACK_USED_LOG_FILE, PROCESSED_ARCHIVES_LOG_FILE, PROCESSED_STANDALONE_LOG_FILE
    global PATH_TOO_LONG_LOG_FILE, EXIFTOOL_FAILURES_LOG_FILE, CORRUPT_ARCHIVES_LOG_FILE
    global CONFIG

    PROJECT_ROOT = cfg.project_root
    WORKBENCH_DIR = cfg.workbench_dir
    EXTRACT_TARGET_DIR = cfg.extract_target_dir
    JSON_REPOSITORY_DIR = cfg.json_repository_dir
    TAKEOUT_ARCHIVES_DIR = cfg.takeout_archives_dir
    TOOLS_DIR = cfg.tools_dir
    EXIFTOOL_DIR_BASE = cfg.exiftool_dir_base
    EXIFTOOL_DIR_EXTRA_FILES = cfg.exiftool_dir_extra_files
    EXIFTOOL_EXE = cfg.exiftool_exe
    EXIFTOOL_PERL = cfg.exiftool_perl
    EXIFTOOL_SCRIPT = cfg.exiftool_script
    FINAL_LIBRARY_DIR = cfg.final_library_dir
    NEEDS_REVIEW_DIR = cfg.needs_review_dir
    ORPHAN_MEDIA_DIR = cfg.orphan_media_dir
    PATH_TOO_LONG_DIR = cfg.path_too_long_dir
    PROCESSED_LOG_FILE = cfg.processed_log_file
    PROCESSED_WORK_ITEMS_LOG_FILE = cfg.processed_work_items_log_file
    FALLBACK_USED_LOG_FILE = cfg.fallback_used_log_file
    PROCESSED_ARCHIVES_LOG_FILE = cfg.processed_archives_log_file
    PROCESSED_STANDALONE_LOG_FILE = cfg.processed_standalone_log_file
    PATH_TOO_LONG_LOG_FILE = cfg.path_too_long_log_file
    EXIFTOOL_FAILURES_LOG_FILE = cfg.exiftool_failures_log_file
    CORRUPT_ARCHIVES_LOG_FILE = cfg.corrupt_archives_log_file
    CONFIG = cfg


def resolve_config(cfg: ProcessMediaConfig | None) -> ProcessMediaConfig:
    return cfg or CONFIG

MAX_PATH_LENGTH = 240  # Windows 11 limit is 260, but we use 240 for safety buffer
# -------------------

# --- Path Configuration (for tests and future flexibility) ---
def configure_paths(project_root, final_library_dir=None):
    """Recompute all path globals from a project root (and optional final library root).
    This keeps behavior identical while allowing tests to override paths safely.
    """
    cfg = build_config(project_root, final_library_dir)
    apply_config(cfg)
    return cfg

# --- Pass 2 ---


def run_pass2(cfg, is_live_run, batch_size, archive_name, force_extract, clean_workbench, show_status):
    # Handle status report first
    if show_status:
        print_status_report(cfg)
        return

    if isinstance(sys.stdout, io.TextIOWrapper):
        try:
            sys.stdout.reconfigure(line_buffering=True, errors="replace")
        except Exception:
            pass

    def _safe_print(message: str) -> None:
        try:
            print(message, flush=True)
            return
        except (OSError, UnicodeEncodeError):
            pass

        # Fallback: write a safe-encoded line directly to the buffer if available.
        try:
            encoding = sys.stdout.encoding or "utf-8"
            if hasattr(sys.stdout, "buffer"):
                data = (message + "\n").encode(encoding, errors="backslashreplace")
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
                return
        except Exception:
            pass

        # Last resort: best-effort ASCII print
        try:
            safe = message.encode("utf-8", errors="backslashreplace").decode("ascii", errors="backslashreplace")
            print(safe, flush=True)
        except Exception:
            pass

    def log(message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _safe_print(f"[{timestamp}] {message}")

    log("=============================================")
    log("=    Pass 2: Process Media Files (V6.2)     =")
    log("=============================================")
    if is_live_run:
        log("*** RUNNING IN LIVE MODE. FILES WILL BE MODIFIED AND MOVED. ***")
    else:
        log("*** RUNNING IN DRY RUN MODE. NO FILES WILL BE CHANGED. ***")
    if batch_size:
        log(f"*** Operating in BATCH MODE. Will process a maximum of {batch_size} work item(s) (archives or standalone files). ***")

    # --- Sanity Checks ---
    if not os.path.isdir(cfg.json_repository_dir):
        sys.exit("FATAL: JSON repository not found. Please run Pass 1 first.")
    if not os.path.isdir(cfg.takeout_archives_dir):
        sys.exit(f"FATAL: Takeout archives directory not found: '{cfg.takeout_archives_dir}'")
    if not os.path.exists(cfg.exiftool_exe) and not os.path.exists(cfg.exiftool_perl):
        sys.exit(f"FATAL: ExifTool not found. Expected under: {cfg.exiftool_dir_base}")

    if not archive_name and (force_extract or clean_workbench):
        if os.path.exists(cfg.processed_log_file):
            try:
                os.remove(cfg.processed_log_file)
                log("Cleared processed media log (--force-extract/--clean-workbench without --archive-name).")
            except Exception as exc:
                log(f"WARNING: Failed to clear processed media log: {exc}")

    processed_work_items = get_processed_work_items(cfg=cfg)
    processed_media_files = get_processed_files_log(cfg=cfg)

    work_items = select_work_items(cfg, archive_name, force_extract, processed_work_items, log)
    if not work_items:
        return

    work_items = sorted(work_items, key=lambda item: os.path.basename(item[1]).lower())
    if batch_size:
        work_items = work_items[:batch_size]
    log(f"Selected {len(work_items)} work item(s) for this run.")

    json_lookup = build_json_lookup(cfg.json_repository_dir, cfg=cfg)
    if not json_lookup:
        log("JSON repository is empty.")
    log(f"Found {len(processed_media_files)} previously processed files in the log.")

    archive_items = [item for item in work_items if item[0] == "archive"]
    for item_type, item_path in work_items:
        if item_type == "archive":
            archive_completed = False
            matches_count = 0
            try:
                archive_size_gb = os.path.getsize(item_path) / (1024 ** 3)
                log(f"Preparing to extract archive: '{item_path}' ({archive_size_gb:.2f} GB)")
                extract_start = time.time()
                extract_archive_to_workbench(item_path, True, cfg=cfg)
                log(f"Extraction completed in {time.time() - extract_start:.1f}s")

                if not os.path.isdir(cfg.extract_target_dir):
                    log(f"WARNING: Workbench extraction directory not found: '{cfg.extract_target_dir}'")
                elif not workbench_has_files(cfg):
                    log("WARNING: Workbench contains no files. Only standalone media in takeout-archives can be matched.")

                # Process media files in workbench (media-driven)
                archive_media_files = list_media_files(cfg.extract_target_dir)
                processed_count, matches_count, warnings_count, errors_count = process_media_files(
                    archive_media_files,
                    cfg,
                    json_lookup,
                    processed_media_files,
                    is_live_run,
                    log,
                    max_path_length=MAX_PATH_LENGTH,
                    get_exif_datetime_fn=get_exif_datetime,
                    get_real_extension_fn=get_real_extension_from_exiftool,
                    normalize_media_extension_fn=normalize_media_extension,
                    run_exiftool_fn=run_exiftool,
                    get_embedded_gps_fn=get_embedded_gps,
                )
                log(f"Archive summary: {processed_count} processed, {matches_count} matched, {warnings_count} warnings, {errors_count} errors.")

                archive_completed = True
            except Exception as e:
                log(f"FATAL: Archive processing failed for '{os.path.basename(item_path)}': {e}")

            if archive_completed and is_live_run:
                log(f"Marking archive as processed: '{os.path.basename(item_path)}'")
                archive_key = normalize_archive_key(os.path.basename(item_path))
                log_processed_work_item(archive_key, cfg=cfg)

            if archive_completed and (clean_workbench or len(archive_items) > 1):
                log("Cleaning workbench extraction directory.")
                shutil.rmtree(cfg.extract_target_dir, ignore_errors=True)
                os.makedirs(cfg.extract_target_dir, exist_ok=True)
                log("Workbench cleanup complete.")
        else:
            log(f"Standalone processing is disabled. Skipping '{item_path}'.")

    log("-" * 45)
    log("Pass 2 Complete for this run.")
    log("=============================================")
    if clean_workbench and os.path.isdir(cfg.extract_target_dir):
        log("Cleaning workbench extraction directory.")
        shutil.rmtree(cfg.extract_target_dir, ignore_errors=True)
        os.makedirs(cfg.extract_target_dir, exist_ok=True)
        log("Workbench cleanup complete.")

# --- Main Processing Logic ---
def main(is_live_run, batch_size, archive_name, force_extract, clean_workbench, show_status):
    cfg = configure_paths(PROJECT_ROOT, FINAL_LIBRARY_DIR)
    run_pass2(cfg, is_live_run, batch_size, archive_name, force_extract, clean_workbench, show_status)
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process and organize media files from Google Takeout.")
    parser.add_argument("--status", action="store_true", help="Display status report of all logs and progress, then exit.")
    parser.add_argument("--live", action="store_true", help="Run in live mode to actually modify and move files.")
    parser.add_argument("--batch-size", type=int, help="Process only a specific number of archives/standalone files and then stop.")
    parser.add_argument("--archive-name", help="Name or full path of a .zip or standalone media file to process.")
    parser.add_argument(
        "--force-extract",
        action="store_true",
        help=(
            "Clear existing workbench contents before extracting. "
            "When used without --archive-name, also clears workbench/.processed_files.log."
        ),
    )
    parser.add_argument(
        "--clean-workbench",
        action="store_true",
        help=(
            "Clear workbench contents after the run completes. "
            "When used without --archive-name, also clears workbench/.processed_files.log at start."
        ),
    )
    args = parser.parse_args()
    main(args.live, args.batch_size, args.archive_name, args.force_extract, args.clean_workbench, args.status)
