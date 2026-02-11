#!/usr/bin/env python3
"""
ExifTool helpers for Pass 2 processing.
"""

from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from process_media_config import ProcessMediaConfig


def build_exiftool_command(args, use_perl: bool = False, cfg: ProcessMediaConfig | None = None):
    if cfg is None:
        raise ValueError("cfg is required for build_exiftool_command")
    if not use_perl and os.path.exists(cfg.exiftool_exe):
        return [os.fspath(cfg.exiftool_exe)] + args
    return [os.fspath(cfg.exiftool_perl), os.fspath(cfg.exiftool_script)] + args


def exiftool_filetype_extension(path, cfg: ProcessMediaConfig | None = None):
    """
    Returns the real extension (e.g. '.jpg') based on file content via ExifTool.
    Falls back to the current suffix if ExifTool can't determine it.
    """
    if cfg is None:
        raise ValueError("cfg is required for exiftool_filetype_extension")
    try:
        cp = subprocess.run(
            [os.fspath(cfg.exiftool_exe), "-s3", "-FileTypeExtension", os.fspath(path)],
            capture_output=True,
            text=True,
            cwd=os.fspath(cfg.exiftool_dir_base),
        )
        ext = (cp.stdout or "").strip().lower()
        if ext and ext != "none":
            return "." + ext
    except Exception:
        pass
    return Path(path).suffix


def normalize_media_extension(path, cfg: ProcessMediaConfig | None = None):
    """
    If file contents disagree with the filename extension (e.g. JPEG named .HEIC),
    rename the file in place and return the new path.
    If a collision exists, it will NOT overwrite; it logs and returns the original path.
    """
    if cfg is None:
        raise ValueError("cfg is required for normalize_media_extension")
    p = Path(path)
    real_ext = exiftool_filetype_extension(p, cfg)
    if not real_ext:
        return os.fspath(p)

    if p.suffix.lower() == real_ext.lower():
        return os.fspath(p)

    new_path = p.with_suffix(real_ext)
    if new_path.exists():
        # Don't overwrite anything. This is rare, but safer to bail than to destroy data.
        print(
            f"WARNING: Type/extension mismatch for '{p.name}' (real {real_ext}), "
            f"but '{new_path.name}' already exists. Leaving as-is."
        )
        return os.fspath(p)

    os.replace(os.fspath(p), os.fspath(new_path))
    print(f"NOTE: Renamed mis-extended file: '{p.name}' -> '{new_path.name}'")
    return os.fspath(new_path)


def _run_exiftool_command(args, cfg: ProcessMediaConfig):
    # Run from EXIFTOOL_DIR so exiftool.exe can reliably find its bundled DLLs/runtime.
    cwd = os.fspath(cfg.exiftool_dir_base)

    def _run(cmd):
        # NOTE: no check=True so we can inspect stdout/stderr ourselves
        return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)

    return _run, cwd


def run_exiftool(args, cfg: ProcessMediaConfig | None = None):
    # Run from EXIFTOOL_DIR so exiftool.exe can reliably find its bundled DLLs/runtime.
    if cfg is None:
        raise ValueError("cfg is required for run_exiftool")
    _run, _ = _run_exiftool_command(args, cfg)

    def _clean(s: str | None, limit: int = 4000) -> str:
        if not s:
            return ""
        s = s.replace("\r", "").strip()
        if len(s) > limit:
            s = s[-limit:]  # keep tail (usually most relevant)
        return s.replace("\n", "\\n")  # keep single-line logs

    def _fmt(cp):
        return (
            f"rc={cp.returncode} "
            f"cmd={cp.args} "
            f"stdout={_clean(cp.stdout)} "
            f"stderr={_clean(cp.stderr)}"
        )

    # Try exiftool.exe first
    if os.path.exists(cfg.exiftool_exe):
        cp = _run(build_exiftool_command(args, cfg=cfg))
        if cp.returncode == 0:
            return cp

        # Fall back to perl+exiftool.pl
        if os.path.exists(cfg.exiftool_perl):
            cp2 = _run(build_exiftool_command(args, use_perl=True, cfg=cfg))
            if cp2.returncode == 0:
                return cp2
            raise RuntimeError(f"ExifTool failed (exe then perl): exe[{_fmt(cp)}] perl[{_fmt(cp2)}]")

        raise RuntimeError(f"ExifTool failed (exe): {_fmt(cp)}")

    # No exe; try perl
    if os.path.exists(cfg.exiftool_perl):
        cp = _run(build_exiftool_command(args, use_perl=True, cfg=cfg))
        if cp.returncode == 0:
            return cp
        raise RuntimeError(f"ExifTool failed (perl): {_fmt(cp)}")

    raise FileNotFoundError(f"No usable ExifTool found under: {cfg.exiftool_dir_base}")


def run_exiftool_read(args, cfg: ProcessMediaConfig | None = None):
    """Run ExifTool for read-only queries.
    Accepts stdout even if ExifTool exits non-zero (warnings are common).
    """
    if cfg is None:
        raise ValueError("cfg is required for run_exiftool_read")
    _run, _ = _run_exiftool_command(args, cfg)

    def _has_stdout(cp):
        return bool((cp.stdout or "").strip())

    if os.path.exists(cfg.exiftool_exe):
        cp = _run(build_exiftool_command(args, cfg=cfg))
        if cp.returncode == 0 or _has_stdout(cp):
            return cp
        if os.path.exists(cfg.exiftool_perl):
            cp2 = _run(build_exiftool_command(args, use_perl=True, cfg=cfg))
            if cp2.returncode == 0 or _has_stdout(cp2):
                return cp2
            raise RuntimeError(f"ExifTool failed (exe then perl): rc={cp.returncode} -> rc={cp2.returncode}")
        raise RuntimeError(f"ExifTool failed (exe): rc={cp.returncode}")

    if os.path.exists(cfg.exiftool_perl):
        cp = _run(build_exiftool_command(args, use_perl=True, cfg=cfg))
        if cp.returncode == 0 or _has_stdout(cp):
            return cp
        raise RuntimeError(f"ExifTool failed (perl): rc={cp.returncode}")

    raise FileNotFoundError(f"No usable ExifTool found under: {cfg.exiftool_dir_base}")


def get_exif_datetime(media_path, cfg: ProcessMediaConfig | None = None, run_exiftool_fn=None):
    if cfg is None:
        raise ValueError("cfg is required for get_exif_datetime")
    run_exiftool_fn = run_exiftool_fn or run_exiftool_read
    try:
        result = run_exiftool_fn(
            [
                "-s",
                "-s",
                "-s",
                "-DateTimeOriginal",
                "-CreateDate",
                "-MediaCreateDate",
                "-TrackCreateDate",
                "-QuickTime:CreateDate",
                media_path,
            ],
            cfg=cfg,
        )
        for line in result.stdout.splitlines():
            match = re.search(r"(\d{4}:\d{2}:\d{2} \d{2}:\d{2}:\d{2})", line)
            if match:
                return datetime.strptime(match.group(1), "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None
    return None


def get_embedded_gps(media_path, cfg: ProcessMediaConfig | None = None, run_exiftool_fn=None):
    """Check if media file already has valid GPS coordinates embedded.
    Returns (has_gps, is_valid) tuple.
    """
    if cfg is None:
        raise ValueError("cfg is required for get_embedded_gps")
    run_exiftool_fn = run_exiftool_fn or run_exiftool
    try:
        # Use numeric output to avoid DMS string parsing issues
        result = run_exiftool_fn(
            ["-n", "-s", "-s", "-s", "-GPSLatitude", "-GPSLongitude", media_path],
            cfg=cfg,
        )
        output = result.stdout.strip()
        if not output:
            return False, False

        lines = output.splitlines()
        if len(lines) < 2:
            return False, False

        # Parse latitude and longitude
        lat_str = lines[0].strip()
        lon_str = lines[1].strip()

        if not lat_str or not lon_str:
            return False, False

        try:
            lat = float(lat_str)
            lon = float(lon_str)
        except (ValueError, TypeError):
            # Tags present but non-numeric; treat as invalid so supplemental can fill
            return True, False

        # Invalid only if BOTH lat AND lon are close to 0 (Null Island)
        # Points on equator (lat=0) or prime meridian (lon=0) are valid
        if abs(lat) < 0.0001 and abs(lon) < 0.0001:
            return True, False

        return True, True
    except Exception:
        return False, False


def get_real_extension_from_exiftool(path, cfg: ProcessMediaConfig | None = None):
    """Return extension like '.jpg' based on file content, not filename."""
    if cfg is None:
        raise ValueError("cfg is required for get_real_extension_from_exiftool")
    return exiftool_filetype_extension(path, cfg)
