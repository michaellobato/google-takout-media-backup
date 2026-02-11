#!/usr/bin/env python3
"""
Status reporting helpers for Pass 2 processing.
"""

from __future__ import annotations

import os

from process_media_config import ProcessMediaConfig
from process_media_logs import get_processed_work_items


def print_status_report(cfg: ProcessMediaConfig | None = None, get_processed_work_items_fn=None):
    """Print a comprehensive status report of all logs and progress."""
    if cfg is None:
        raise ValueError("cfg is required for print_status_report")
    get_processed_work_items_fn = get_processed_work_items_fn or get_processed_work_items

    print("=" * 60)
    print("PROJECT STATUS REPORT".center(60))
    print("=" * 60)
    print()

    # Count archives
    total_archives = len([f for f in os.listdir(cfg.takeout_archives_dir) if f.lower().endswith('.zip')])
    processed_work_items = get_processed_work_items_fn(cfg=cfg)
    processed_archives = len([k for k in processed_work_items if k.startswith('archive:')])

    print(f"Pass 2 Progress:")
    print(f"  Archives processed: {processed_archives} / {total_archives}")

    # Count processed files
    if os.path.exists(cfg.processed_log_file):
        with open(cfg.processed_log_file, 'r') as f:
            total_files = sum(1 for _ in f)
        print(f"  Media files processed: {total_files:,}")
    else:
        print(f"  Media files processed: 0")

    print()
    print("=" * 60)
    print("ISSUES REQUIRING ATTENTION".center(60))
    print("=" * 60)

    # Check each issue log
    issues = []

    if os.path.exists(cfg.exiftool_failures_log_file):
        with open(cfg.exiftool_failures_log_file, 'r') as f:
            count = sum(1 for _ in f)
        if count > 0:
            issues.append(f"  [WARN] ExifTool failures: {count} files")

    if os.path.exists(cfg.path_too_long_log_file):
        with open(cfg.path_too_long_log_file, 'r') as f:
            count = sum(1 for _ in f)
        if count > 0:
            issues.append(f"  [WARN] Path too long: {count} files")

    if os.path.exists(cfg.corrupt_archives_log_file):
        with open(cfg.corrupt_archives_log_file, 'r') as f:
            count = sum(1 for _ in f)
        if count > 0:
            issues.append(f"  [ERROR] Corrupt archives: {count}")

    if issues:
        print()
        for issue in issues:
            print(issue)
    else:
        print()
        print("  [OK] No issues found!")

    print()
    print("=" * 60)
    print("LOG FILE LOCATIONS".center(60))
    print("=" * 60)
    print()
    print("Progress Logs (for resuming):")
    print(f"  {cfg.processed_log_file}")
    print(f"  {cfg.processed_work_items_log_file}")
    print()
    print("Issue Logs (for review):")
    print(f"  {cfg.exiftool_failures_log_file}")
    print(f"  {cfg.path_too_long_log_file}")
    print(f"  {cfg.corrupt_archives_log_file}")
    print()
    print("Review Folders:")
    print(f"  {cfg.needs_review_dir}")
    print()
    print("=" * 60)
