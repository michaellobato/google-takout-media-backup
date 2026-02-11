#!/usr/bin/env python3
"""
Workflow helpers for Pass 2 processing.
"""

from __future__ import annotations

import os
import shutil
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from process_media_config import ProcessMediaConfig
from process_media_exif import (
    get_exif_datetime,
    get_real_extension_from_exiftool,
    normalize_media_extension,
    run_exiftool,
    get_embedded_gps,
)
from process_media_json import get_timestamp_from_json, get_valid_gps_from_supplemental
from process_media_logs import (
    normalize_archive_key,
    log_processed_file,
    log_path_too_long,
    log_exiftool_failure,
)
from process_media_matching import match_json_for_media
from process_media_paths import resolve_archive_path, validate_path_length


def list_media_files(root_dir):
    media_files = []
    for root, _, files in os.walk(root_dir):
        for filename in files:
            if filename.lower().endswith(".json"):
                continue
            media_files.append(os.path.join(root, filename))
    return sorted(media_files)


def copy_jsons(json_paths, dest_dir):
    for path in sorted(set(json_paths)):
        dest_path = os.path.join(dest_dir, os.path.basename(path))
        if not os.path.exists(dest_path):
            shutil.copy2(path, dest_path)


def pick_timestamp_from_json_list(json_paths):
    for path in sorted(json_paths):
        ts = get_timestamp_from_json(path)
        if ts:
            return ts
    return None


def pick_gps_from_json_list(json_paths):
    for path in sorted(json_paths):
        gps = get_valid_gps_from_supplemental(path)
        if gps:
            return gps
    return None


def get_media_bundle_dir(dest_root, media_filename):
    base_name = os.path.splitext(os.path.basename(media_filename))[0]
    return os.path.join(dest_root, base_name)


def select_work_items(cfg, archive_name, force_extract, processed_work_items, log):
    work_items = []

    if archive_name:
        archive_path = resolve_archive_path(archive_name, cfg=cfg)
        if not archive_path:
            sys.exit(f"FATAL: Archive not found: '{archive_name}'")
        if archive_path.lower().endswith(".zip"):
            archive_basename = os.path.basename(archive_path)
            if normalize_archive_key(archive_basename) in processed_work_items and not force_extract:
                sys.exit(f"FATAL: Archive already marked processed in Pass 2 log: '{archive_basename}'")
            work_items = [("archive", archive_path)]
        else:
            sys.exit("FATAL: Standalone processing is disabled. Provide a .zip archive.")
    else:
        zip_files = sorted(f for f in os.listdir(cfg.takeout_archives_dir) if f.lower().endswith(".zip"))
        if not zip_files:
            sys.exit("FATAL: No .zip archives found in takeout-archives.")
        zip_files_to_try = [z for z in zip_files if normalize_archive_key(z) not in processed_work_items]
        if not zip_files_to_try:
            sys.exit("FATAL: All archives appear processed in Pass 2 log.")
        for zip_name in zip_files_to_try:
            work_items.append(("archive", os.path.join(cfg.takeout_archives_dir, zip_name)))

    if not work_items:
        log("WARNING: No work items selected. Use --archive-name to target a specific archive.")

    return work_items


def process_media_files(
    media_files,
    cfg,
    json_lookup,
    processed_media_files,
    is_live_run,
    log,
    max_path_length,
    get_exif_datetime_fn=None,
    get_real_extension_fn=None,
    normalize_media_extension_fn=None,
    run_exiftool_fn=None,
    get_embedded_gps_fn=None,
):
    get_exif_datetime_fn = get_exif_datetime_fn or get_exif_datetime
    get_real_extension_fn = get_real_extension_fn or get_real_extension_from_exiftool
    normalize_media_extension_fn = normalize_media_extension_fn or normalize_media_extension
    run_exiftool_fn = run_exiftool_fn or run_exiftool
    get_embedded_gps_fn = get_embedded_gps_fn or get_embedded_gps
    files_processed_this_run = 0
    matches_found = 0
    warnings_found = 0
    errors_found = 0

    for media_file_path in media_files:
        if media_file_path in processed_media_files:
            continue

        base_name = os.path.basename(media_file_path)
        primary_jsons, supplemental_jsons = match_json_for_media(base_name, json_lookup)
        matched_jsons = primary_jsons + supplemental_jsons

        if matched_jsons:
            matches_found += 1
            log(f"Matched JSON for '{base_name}' (primary={len(primary_jsons)}, supplemental={len(supplemental_jsons)})")
        else:
            log(f"No JSON match for '{base_name}'")

        try:
            embedded_dt = get_exif_datetime_fn(media_file_path, cfg=cfg)
            timestamp_source = None
            date = None

            if embedded_dt:
                date = embedded_dt
                timestamp_source = "embedded"
            else:
                primary_ts = pick_timestamp_from_json_list(primary_jsons)
                if primary_ts:
                    date = datetime.fromtimestamp(primary_ts, timezone.utc)
                    timestamp_source = "primary_json"
                else:
                    supplemental_ts = pick_timestamp_from_json_list(supplemental_jsons)
                    if supplemental_ts:
                        date = datetime.fromtimestamp(supplemental_ts, timezone.utc)
                        timestamp_source = "supplemental"

            if not date:
                log(f"   - WARNING: No usable timestamp (embedded/JSON/supplemental) for '{base_name}'. Sending to needs review.")
                warnings_found += 1
                if is_live_run:
                    os.makedirs(cfg.orphan_media_dir, exist_ok=True)
                    dest_path = os.path.join(cfg.orphan_media_dir, base_name)
                    if not os.path.exists(dest_path):
                        shutil.move(media_file_path, dest_path)
                    copy_jsons(matched_jsons, cfg.orphan_media_dir)
                    log_processed_file(media_file_path, cfg=cfg)
                processed_media_files.add(media_file_path)
                continue

            year, month = date.strftime("%Y"), date.strftime("%m")
            dest_root = os.path.join(cfg.final_library_dir, year, month)
            dest_dir = get_media_bundle_dir(dest_root, media_file_path)
            src = Path(media_file_path)
            real_ext = get_real_extension_fn(media_file_path, cfg)
            dest_media_path = os.path.join(dest_dir, src.stem + real_ext)

            # Validate path length before operations
            is_valid, path_len = validate_path_length(dest_media_path, max_path_length)
            if not is_valid:
                log(f"   - WARNING: Destination path too long ({path_len} chars, max {max_path_length})")
                log(f"   - Moving to path-too-long review folder: '{base_name}'")
                if is_live_run:
                    os.makedirs(cfg.path_too_long_dir, exist_ok=True)
                    fallback_dest = os.path.join(cfg.path_too_long_dir, base_name)
                    if not os.path.exists(fallback_dest):
                        shutil.move(media_file_path, fallback_dest)
                    copy_jsons(matched_jsons, cfg.path_too_long_dir)
                    log_path_too_long(media_file_path, dest_media_path, path_len, cfg=cfg)
                    log_processed_file(media_file_path, cfg=cfg)
                warnings_found += 1
                processed_media_files.add(media_file_path)
                continue

            if is_live_run:
                os.makedirs(dest_dir, exist_ok=True)
                if os.path.exists(dest_media_path):
                    log(f"   - WARNING: Media file already exists in destination. Skipping.")
                    warnings_found += 1
                    if matched_jsons:
                        copy_jsons(matched_jsons, dest_dir)
                        log(f"   - Copied {len(matched_jsons)} JSON file(s) to '{dest_dir}'")
                    log_processed_file(media_file_path, cfg=cfg)
                    files_processed_this_run += 1
                else:
                    shutil.move(media_file_path, dest_media_path)
                    log(f"   - Moved media from workbench to '{dest_dir}'")

                    dest_media_path = normalize_media_extension_fn(dest_media_path, cfg=cfg)
                    if timestamp_source == "primary_json":
                        exif_dt = date.strftime("%Y:%m:%d %H:%M:%S")
                        exif_cmd = [
                            f"-DateTimeOriginal={exif_dt}",
                            f"-CreateDate={exif_dt}",
                            f"-FileModifyDate={exif_dt}",
                            "-overwrite_original", "-P", dest_media_path
                        ]
                        try:
                            run_exiftool_fn(exif_cmd, cfg=cfg)
                            if primary_jsons:
                                log(f"   - Merged timestamps from primary JSON ('{os.path.basename(primary_jsons[0])}')")
                        except Exception as e:
                            log(f"   - WARNING: Failed to merge timestamps from primary JSON: {e}")
                            log_exiftool_failure(media_file_path, f"primary_json: {str(e)}", cfg=cfg)

                    elif timestamp_source == "supplemental":
                        exif_dt = date.strftime("%Y:%m:%d %H:%M:%S")
                        exif_cmd = [
                            f"-DateTimeOriginal={exif_dt}",
                            f"-CreateDate={exif_dt}",
                            f"-FileModifyDate={exif_dt}",
                            "-overwrite_original", "-P", dest_media_path
                        ]
                        try:
                            run_exiftool_fn(exif_cmd, cfg=cfg)
                            log(f"   - Merged timestamps from supplemental metadata")
                        except Exception as e:
                            log(f"   - WARNING: Failed to merge timestamps from supplemental metadata: {e}")
                            log_exiftool_failure(media_file_path, f"supplemental_timestamp: {str(e)}", cfg=cfg)

                    copy_jsons(matched_jsons, dest_dir)
                    if matched_jsons:
                        log(f"   - Copied {len(matched_jsons)} JSON file(s) to '{dest_dir}'")

                    if supplemental_jsons:
                        has_gps, gps_valid = get_embedded_gps_fn(dest_media_path, cfg=cfg)
                        if not has_gps or not gps_valid:
                            valid_gps = pick_gps_from_json_list(supplemental_jsons)
                            if valid_gps:
                                lat, lon, alt = valid_gps
                                try:
                                    exif_cmd = [
                                        "-GPSLatitude=" + str(lat),
                                        "-GPSLongitude=" + str(lon),
                                        "-GPSAltitude=" + str(alt),
                                        "-overwrite_original", "-P", dest_media_path
                                    ]
                                    run_exiftool_fn(exif_cmd, cfg=cfg)
                                    log(f"   - Added GPS from supplemental metadata")
                                except Exception as e:
                                    log(f"   - WARNING: Failed to merge GPS data: {e}")
                                    log_exiftool_failure(media_file_path, f"supplemental_gps: {str(e)}", cfg=cfg)

                    log_processed_file(media_file_path, cfg=cfg)
                    files_processed_this_run += 1
            else:
                log(f"   - [DRY RUN] Would move media to '{dest_dir}'")
                if timestamp_source == "primary_json":
                    log(f"   - [DRY RUN] Would embed timestamps from primary JSON")
                elif timestamp_source == "supplemental":
                    log(f"   - [DRY RUN] Would embed timestamps from supplemental metadata")
                else:
                    log(f"   - [DRY RUN] Would preserve embedded timestamps")
                if matched_jsons:
                    log(f"   - [DRY RUN] Would copy {len(matched_jsons)} JSON file(s) to '{dest_dir}'")
                files_processed_this_run += 1

            processed_media_files.add(media_file_path)

        except Exception as e:
            log(f"   - ERROR processing '{base_name}': {e}")
            log(f"   - Stack trace: {traceback.format_exc()}")
            errors_found += 1
            continue

    return files_processed_this_run, matches_found, warnings_found, errors_found
