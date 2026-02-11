#!/usr/bin/env python3
"""
Indexing helpers for media lookup.
"""

from __future__ import annotations

import os


def build_media_index(source_dirs, allowed_paths=None):
    """Build a dictionary mapping lowercase filenames to list of full paths.
    This is done ONCE at startup instead of walking directories repeatedly."""
    print("Building media file index (this may take a minute)...", flush=True)
    index = {}
    total_files = 0
    for source_dir in source_dirs:
        if not os.path.exists(source_dir):
            continue
        for root, dirs, files in os.walk(source_dir):
            dirs.sort()
            for file in files:
                if file.lower().endswith('.json'):
                    continue
                full_path = os.path.join(root, file)
                if allowed_paths is not None and full_path not in allowed_paths:
                    continue
                # Use lowercase for case-insensitive matching
                key = file.lower()
                if key not in index:
                    index[key] = []
                index[key].append(full_path)
                total_files += 1
                if total_files % 10000 == 0:
                    print(f"  Indexed {total_files} media files...", flush=True)
    print(f"Media index complete: {total_files} files indexed.", flush=True)
    return index


def find_media_file_from_index(filename_candidates, processed_files_set, media_index):
    """Look up media files using pre-built index instead of walking directories."""
    for candidate in filename_candidates:
        candidate_lower = candidate.lower()
        if candidate_lower in media_index:
            for full_path in media_index[candidate_lower]:
                if full_path not in processed_files_set:
                    return full_path
    return None
