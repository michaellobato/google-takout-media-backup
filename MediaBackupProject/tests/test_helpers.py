#!/usr/bin/env python3
"""
Shared helpers for tests (no external dependencies).
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def load_process_media():
    script_path = Path(__file__).resolve().parent.parent / "scripts" / "2-process-media.py"
    loader = importlib.machinery.SourceFileLoader("process_media", str(script_path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@contextmanager
def temp_dir():
    path = Path(tempfile.mkdtemp())
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def assert_safe_paths(module, temp_root: Path):
    """Hard guard to prevent tests from touching real data paths."""
    temp_root = Path(temp_root).resolve()
    forbidden_drives = {"P:", "Z:"}

    def _drive(path: Path) -> str:
        return (path.drive or "").upper()

    critical_paths = [
        Path(module.PROJECT_ROOT),
        Path(module.TAKEOUT_ARCHIVES_DIR),
        Path(module.JSON_REPOSITORY_DIR),
        Path(module.WORKBENCH_DIR),
        Path(module.FINAL_LIBRARY_DIR),
        Path(module.NEEDS_REVIEW_DIR),
    ]

    for p in critical_paths:
        p = Path(p).resolve()
        if _drive(p) in forbidden_drives:
            raise RuntimeError(f"Unsafe test path (forbidden drive): {p}")
        try:
            if not str(p).lower().startswith(str(temp_root).lower()):
                raise RuntimeError(f"Unsafe test path (outside temp root): {p}")
        except Exception:
            raise RuntimeError(f"Unsafe test path: {p}")


@contextmanager
def patched(module, **kwargs):
    originals = {key: getattr(module, key) for key in kwargs}
    try:
        for key, value in kwargs.items():
            setattr(module, key, value)
        yield
    finally:
        for key, value in originals.items():
            setattr(module, key, value)
