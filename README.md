# MediaBackupProject (personal tool, not plug-and-play)

This repo contains a personal, custom Google Photos Takeout processing tool. It is **not** a general-purpose utility and **not** intended for public use without significant modification.

TL;DR: This is a pragmatic, one-off workflow built for a specific environment. It has hard-coded paths, assumes a specific folder layout, and relies on external tools that are **not included** in this repo.

---

## What this is

A set of scripts that:

- Extract Google Takeout metadata JSONs.
- Match metadata to media.
- Prefer embedded metadata, then primary JSON, then supplemental JSON.
- Organize media into `YYYY/MM/<BaseName>/` bundle folders.
- Write EXIF timestamps when needed.

---

## What this is not

- Not a reusable library.
- Not a drop-in CLI tool.
- Not tested for arbitrary environments.
- Not safe to run without careful review.

---

## Major caveats

- **Hard-coded paths**  
  The scripts assume Windows paths and specific drive letters (for example, `P:\` and `Z:\`). You must edit configuration or `MediaBackupProject/scripts/2-process-media.py` defaults for your system.

- **ExifTool required (not included)**  
  The workflow depends on ExifTool being present under:
  ```
  MediaBackupProject/tools/exiftool-13.48_64/
  ```
  This directory is **not** in the repo. You must download and place ExifTool manually.

- **Environment-specific**  
  The tool assumes Windows + local filesystem behavior. macOS/Linux will need path and behavior adjustments.

- **Google Takeout quirks**  
  Matching logic is tailored to Google Takeout JSON formats, including `.supplemental-metadata.json` and `.sup.json`.

- **No warranty**  
  This code can modify files. Use dry-run first, verify outputs, and keep backups.

---

## Repo layout

The actual project is inside:

```
MediaBackupProject/
```

Key folders inside that directory:

- `scripts/` - main workflow (`2-process-media.py`, `1-extract-json.py`)
- `tests/` - local test suite
- `json-repository/` - extracted metadata
- `takeout-archives/` - Google Takeout zip files
- `workbench/` - extraction/processing workspace
- `tools/` - ExifTool (not included in repo)

---

## Usage (for reference only)

This is **not guaranteed to work on your machine**.

Dry run (single archive):
```powershell
cd MediaBackupProject\scripts; python 2-process-media.py --batch-size 1 --force-extract
```

Live run (single archive):
```powershell
cd MediaBackupProject\scripts; python 2-process-media.py --batch-size 1 --force-extract --live
```

Tests:
```powershell
cd MediaBackupProject; python tests\test_all.py
```

---

## Why it exists

Google Photos storage costs add up. This was built to:

- Preserve original metadata.
- Organize a large archive offline.
- Make future photo apps usable.

---

## If you want to adapt this

Start with:

- `MediaBackupProject/README.md`
- `MediaBackupProject/scripts/1-extract-json.py`
- `MediaBackupProject/scripts/2-process-media.py`

Expect to rewrite config paths, directory assumptions, and verify metadata behavior for your takeout.

---

## License

No license specified. All rights reserved by the author.
