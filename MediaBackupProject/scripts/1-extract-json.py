# ===================================================================
# 1-extract-json.py
#
# Purpose: Implements Pass 1 of the Two-Pass strategy.
#
# V3 Final: This is the robust, stateful, and performant version.
# It maintains a log of processed archives to make re-runs
# instantaneous. It also uses a more robust streaming extraction
# method to prevent file path errors.
# ===================================================================

import os
import zipfile
import sys
import filecmp
import shutil

# --- Configuration ---
PROJECT_ROOT = "P:/MediaBackupProject"
# CRITICAL: TAKEOUT_ARCHIVES_DIR is IMMUTABLE - never move or modify files here!
TAKEOUT_ARCHIVES_DIR = f"{PROJECT_ROOT}/takeout-archives"
JSON_REPOSITORY_DIR = f"{PROJECT_ROOT}/json-repository"
CORRUPT_ARCHIVES_DIR = f"{PROJECT_ROOT}/corrupt-archives"
JSON_CONFLICTS_DIR = f"{PROJECT_ROOT}/json-conflicts"
# This log file will store the names of successfully processed archives.
PROCESSED_LOG_FILE = f"{PROJECT_ROOT}/.processed_archives.log"
# -------------------

def get_processed_archives():
    """Reads the log file and returns a set of filenames for fast lookups."""
    if not os.path.exists(PROCESSED_LOG_FILE):
        return set()
    with open(PROCESSED_LOG_FILE, 'r') as f:
        # Read lines and strip any whitespace/new characters.
        return set(line.strip() for line in f)

def log_processed_archive(filename):
    """Appends a successfully processed archive name to the log file."""
    with open(PROCESSED_LOG_FILE, 'a') as f:
        f.write(filename + '\n')

def main():
    """Main function to execute the JSON extraction process."""
    print("=============================================")
    print("=      Pass 1: Consolidate JSON Files (V3)  =")
    print("=============================================")

    os.makedirs(JSON_REPOSITORY_DIR, exist_ok=True)
    os.makedirs(CORRUPT_ARCHIVES_DIR, exist_ok=True)
    os.makedirs(JSON_CONFLICTS_DIR, exist_ok=True)

    if not os.path.isdir(TAKEOUT_ARCHIVES_DIR):
        print(f"FATAL: Source directory not found: {TAKEOUT_ARCHIVES_DIR}")
        sys.exit(1)

    # --- Stateful Processing ---
    processed_archives = get_processed_archives()
    print(f"Found {len(processed_archives)} previously processed archives in the log.")

    all_zip_files = [f for f in os.listdir(TAKEOUT_ARCHIVES_DIR) if f.lower().endswith('.zip')]
    # Determine which archives are new and need processing.
    zip_files_to_process = [f for f in all_zip_files if f not in processed_archives]

    if not zip_files_to_process:
        print("No new archives to process. JSON repository is up to date.")
        return

    print(f"Found {len(zip_files_to_process)} new archives to process...")
    total_json_extracted = 0

    for zip_filename in zip_files_to_process:
        full_zip_path = os.path.join(TAKEOUT_ARCHIVES_DIR, zip_filename)
        print(f"\nProcessing '{zip_filename}'...")

        try:
            # IMMUTABILITY: We only READ from archives, extracting JSONs to json-repository
            with zipfile.ZipFile(full_zip_path, 'r') as archive:
                json_files_in_archive = [f for f in archive.namelist() if f.lower().endswith('.json')]
                if not json_files_in_archive:
                    print(" -> No .json files found in this archive.")
                    continue

                for json_path_in_zip in json_files_in_archive:
                    base_filename = os.path.basename(json_path_in_zip)
                    dest_path = os.path.join(JSON_REPOSITORY_DIR, base_filename)

                    # --- V3 Robust Extraction & Conflict Handling ---
                    # Extract to temp location for comparison (never modifies takeout-archives)
                    temp_conflict_path = os.path.join(JSON_CONFLICTS_DIR, base_filename)
                    with archive.open(json_path_in_zip) as source_file:
                        # Write the file from the zip to a temporary location for comparison/moving.
                        with open(temp_conflict_path, 'wb') as temp_target:
                            shutil.copyfileobj(source_file, temp_target)
                    
                    if os.path.exists(dest_path):
                        if filecmp.cmp(dest_path, temp_conflict_path, shallow=False):
                            print(f" -> Skipping '{base_filename}' (identical duplicate found).")
                            os.remove(temp_conflict_path) # Clean up temp file
                        else:
                            conflict_filename = f"{os.path.splitext(base_filename)[0]}_{zip_filename}.json"
                            conflict_dest_path = os.path.join(JSON_CONFLICTS_DIR, conflict_filename)
                            shutil.move(temp_conflict_path, conflict_dest_path)
                            print(f" -> CONFLICT! '{base_filename}' exists with different content. Moved new version to conflicts folder.")
                    else:
                        # No conflict, move the temp file to its final destination.
                        shutil.move(temp_conflict_path, dest_path)
                        total_json_extracted += 1

                print(f" -> Extracted {len(json_files_in_archive)} JSON file(s).")
            
            # If the whole archive is processed successfully, log it.
            log_processed_archive(zip_filename)

        except zipfile.BadZipFile:
            print(f" -> ERROR: Corrupt zip file detected: '{zip_filename}'")
            print(f" -> Archive remains in takeout-archives (immutability rule). Manually review and re-download if needed.")
            # DO NOT MOVE - takeout-archives is immutable. Log it instead.
            with open(f"{PROJECT_ROOT}/.corrupt_archives.log", 'a') as corrupt_log:
                corrupt_log.write(f"{zip_filename}\n")
        except Exception as e:
            print(f" -> An unexpected error occurred: {e}. Skipping this archive.")

    print("-" * 45)
    print(f"Pass 1 Complete. Total new JSON files extracted: {total_json_extracted}")
    print("=============================================")

if __name__ == "__main__":
    main()
