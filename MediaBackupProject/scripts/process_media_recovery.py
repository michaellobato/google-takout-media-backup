#!/usr/bin/env python3
"""
Recovery helpers for fallback processing paths.
"""

from __future__ import annotations

import os
import shutil
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
from process_media_json_lookup import find_all_supplemental_for_basename
from process_media_logs import log_exiftool_failure, log_path_too_long
from process_media_paths import is_under_dir, validate_path_length
from process_media_workflow import get_media_bundle_dir


def copy_supplemental_if_present(
    basename,
    dest_dir,
    supplemental_index,
    find_all_supplemental_fn=None,
    copy_fn=None,
):
    """Copy ALL supplemental metadata files for a given media file.
    Returns count of files copied.
    """
    find_all_supplemental_fn = find_all_supplemental_fn or find_all_supplemental_for_basename
    copy_fn = copy_fn or shutil.copy2

    all_supplemental = find_all_supplemental_fn(basename, supplemental_index)
    if not all_supplemental:
        return 0

    count = 0
    for supplemental_path in all_supplemental:
        dest_path = os.path.join(dest_dir, os.path.basename(supplemental_path))
        if not os.path.exists(dest_path):
            copy_fn(supplemental_path, dest_path)
            count += 1
    return count


def recover_media_with_fallback(
    media_path,
    supplemental_index,
    dest_root,
    is_live_run,
    cfg: ProcessMediaConfig | None = None,
    max_path_length: int = 240,
    get_exif_datetime_fn=None,
    find_all_supplemental_fn=None,
    get_timestamp_from_json_fn=None,
    get_media_bundle_dir_fn=None,
    get_real_extension_fn=None,
    normalize_media_extension_fn=None,
    run_exiftool_fn=None,
    get_embedded_gps_fn=None,
    get_valid_gps_fn=None,
    is_under_dir_fn=None,
    log_path_too_long_fn=None,
    log_exiftool_failure_fn=None,
):
    """Recover media using fallback metadata (EXIF/supplemental).
    IMMUTABILITY: Checks if source is from takeout-archives and copies instead of moving.
    """
    if cfg is None:
        raise ValueError("cfg is required for recover_media_with_fallback")

    get_exif_datetime_fn = get_exif_datetime_fn or get_exif_datetime
    find_all_supplemental_fn = find_all_supplemental_fn or find_all_supplemental_for_basename
    get_timestamp_from_json_fn = get_timestamp_from_json_fn or get_timestamp_from_json
    get_media_bundle_dir_fn = get_media_bundle_dir_fn or get_media_bundle_dir
    get_real_extension_fn = get_real_extension_fn or get_real_extension_from_exiftool
    normalize_media_extension_fn = normalize_media_extension_fn or normalize_media_extension
    run_exiftool_fn = run_exiftool_fn or run_exiftool
    get_embedded_gps_fn = get_embedded_gps_fn or get_embedded_gps
    get_valid_gps_fn = get_valid_gps_fn or get_valid_gps_from_supplemental
    is_under_dir_fn = is_under_dir_fn or is_under_dir
    log_path_too_long_fn = log_path_too_long_fn or log_path_too_long
    log_exiftool_failure_fn = log_exiftool_failure_fn or log_exiftool_failure

    date = get_exif_datetime_fn(media_path, cfg=cfg)
    reason = "exif"
    all_supplemental = find_all_supplemental_fn(os.path.basename(media_path), supplemental_index)
    supplemental_path = all_supplemental[0] if all_supplemental else None
    if not date and supplemental_path:
        timestamp = get_timestamp_from_json_fn(supplemental_path)
        if timestamp:
            date = datetime.fromtimestamp(timestamp, timezone.utc)
            reason = "supplemental"
    # If we don't have real metadata (JSON/EXIF/supplemental), don't fake it with filesystem timestamps
    if not date:
        return False, None

    year, month = date.strftime("%Y"), date.strftime("%m")
    dest_root_dir = os.path.join(dest_root, year, month)
    dest_dir = get_media_bundle_dir_fn(dest_root_dir, media_path)
    src = Path(media_path)
    real_ext = get_real_extension_fn(media_path, cfg)
    dest_media_path = os.path.join(dest_dir, src.stem + real_ext)

    # Validate path length
    is_valid, path_len = validate_path_length(dest_media_path, max_path_length)
    if not is_valid:
        # Path too long - move to special folder instead
        if is_live_run:
            os.makedirs(cfg.path_too_long_dir, exist_ok=True)
            fallback_dest = os.path.join(cfg.path_too_long_dir, os.path.basename(media_path))
            if not os.path.exists(fallback_dest):
                if is_under_dir_fn(media_path, cfg.takeout_archives_dir):
                    shutil.copy2(media_path, fallback_dest)
                    fallback_dest = normalize_media_extension_fn(fallback_dest, cfg=cfg)
                else:
                    shutil.move(media_path, fallback_dest)
                    fallback_dest = normalize_media_extension_fn(fallback_dest, cfg=cfg)
            # Copy all supplemental files for this media file
            for supp_path in all_supplemental:
                supp_dest = os.path.join(cfg.path_too_long_dir, os.path.basename(supp_path))
                if not os.path.exists(supp_dest):
                    shutil.copy2(supp_path, supp_dest)
            log_path_too_long_fn(media_path, dest_media_path, path_len, cfg=cfg)
        return False, None  # Indicate path too long

    if is_live_run:
        os.makedirs(dest_dir, exist_ok=True)
        if not os.path.exists(dest_media_path):
            # IMMUTABILITY: Copy from takeout-archives, move from workbench
            if is_under_dir_fn(media_path, cfg.takeout_archives_dir):
                shutil.copy2(media_path, dest_media_path)
            else:
                shutil.move(media_path, dest_media_path)
        dest_media_path = normalize_media_extension_fn(dest_media_path, cfg=cfg)
        # If we recovered using supplemental timestamp, embed it now
        if reason == "supplemental":
            exif_dt = date.strftime("%Y:%m:%d %H:%M:%S")
            exif_cmd = [
                f"-DateTimeOriginal={exif_dt}",
                f"-CreateDate={exif_dt}",
                f"-FileModifyDate={exif_dt}",
                "-overwrite_original", "-P", dest_media_path
            ]
            try:
                run_exiftool_fn(exif_cmd, cfg=cfg)
            except Exception as e:
                print(f"WARNING: Failed to merge timestamps for {os.path.basename(media_path)}: {e}")
                log_exiftool_failure_fn(media_path, f"supplemental_timestamp: {str(e)}", cfg=cfg)
        # Copy ALL supplemental metadata files
        for supp_path in all_supplemental:
            supp_dest = os.path.join(dest_dir, os.path.basename(supp_path))
            if not os.path.exists(supp_dest):
                shutil.copy2(supp_path, supp_dest)

        # Smart GPS embedding: only add if not already present or if upgrading from 0,0
        if supplemental_path:
            has_gps, gps_valid = get_embedded_gps_fn(dest_media_path, cfg=cfg)

            # Only try to add GPS if: no GPS exists, or GPS is 0,0
            if not has_gps or not gps_valid:
                valid_gps = get_valid_gps_fn(supplemental_path)

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
                    except Exception as e:
                        # Log failure but continue - GPS merge is not critical
                        print(f"WARNING: Failed to merge GPS data for {os.path.basename(media_path)}: {e}")
                        log_exiftool_failure_fn(media_path, f"supplemental_gps: {str(e)}", cfg=cfg)
    return True, reason
