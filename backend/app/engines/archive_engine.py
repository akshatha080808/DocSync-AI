"""Archive extraction engine providing secure ZIP unpack, validation, and project root detection.

Guards implemented:
- Safe temporary staging
- ZIP Slip protection (canonical path boundary check)
- Symlink rejection
- ZIP bomb protection (uncompressed byte budget & compression ratio limits)
- Max file count limit
- Root directory auto-detection (unwrapping single top-level folder)
"""

from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Tuple

from app.core.config import settings
from app.core.exceptions import UploadRejectedError


class ArchiveEngine:
    """Safely inspects and extracts ZIP archives."""

    def __init__(
        self,
        max_upload_bytes: int = settings.max_upload_bytes,
        max_extract_bytes: int = settings.max_extract_bytes,
        max_files: int = settings.max_files,
        max_compression_ratio: int = settings.max_compression_ratio,
    ):
        self.max_upload_bytes = max_upload_bytes
        self.max_extract_bytes = max_extract_bytes
        self.max_files = max_files
        self.max_compression_ratio = max_compression_ratio

    def validate_and_extract_zip(self, zip_path: Path, target_dir: Path) -> Tuple[int, int]:
        """Safely extracts a ZIP archive into target_dir.

        Returns (file_count, total_uncompressed_bytes).
        Raises UploadRejectedError on any safety violation.
        """
        if not zip_path.is_file():
            raise UploadRejectedError(f"Uploaded archive '{zip_path.name}' is not a valid file.")

        file_size = zip_path.stat().st_size
        if file_size > self.max_upload_bytes:
            raise UploadRejectedError(
                f"Archive size {file_size} bytes exceeds maximum allowed limit of {self.max_upload_bytes} bytes."
            )
        if file_size == 0:
            raise UploadRejectedError("Uploaded archive is empty.")

        if not zipfile.is_zipfile(zip_path):
            raise UploadRejectedError("Uploaded file is not a valid ZIP archive.")

        # Stage in temporary directory first
        temp_extract_dir = Path(tempfile.mkdtemp(prefix="docsync_extract_"))
        try:
            total_uncompressed = 0
            file_count = 0

            with zipfile.ZipFile(zip_path, "r") as zf:
                infolist = zf.infolist()
                if len(infolist) > self.max_files:
                    raise UploadRejectedError(
                        f"Archive contains {len(infolist)} entries, exceeding maximum allowed limit of {self.max_files}."
                    )

                # Pre-scan inspection
                for info in infolist:
                    # Check for symlinks
                    # Unix symlinks typically have file_mode upper bits 0o120000
                    mode = info.external_attr >> 16
                    if (mode & 0o170000) == 0o120000:
                        raise UploadRejectedError(
                            f"Archive contains symlink '{info.filename}', which is rejected for security."
                        )

                    total_uncompressed += info.file_size
                    if total_uncompressed > self.max_extract_bytes:
                        raise UploadRejectedError(
                            f"Total uncompressed size exceeds maximum allowed limit of {self.max_extract_bytes} bytes."
                        )

                    # ZIP bomb compression ratio check
                    compressed_size = max(info.compress_size, 1)
                    ratio = info.file_size / compressed_size
                    if ratio > self.max_compression_ratio and info.file_size > 1024 * 1024:
                        raise UploadRejectedError(
                            f"Suspicious compression ratio ({ratio:.1f}x) detected for '{info.filename}'."
                        )

                # Safe extraction with Zip Slip defense
                target_resolved = temp_extract_dir.resolve()
                for info in infolist:
                    filename = info.filename
                    # Normalize and prevent absolute or backslash paths
                    clean_name = filename.replace("\\", "/").lstrip("/")
                    if not clean_name:
                        continue

                    destination = (temp_extract_dir / clean_name).resolve()
                    if not str(destination).startswith(str(target_resolved) + os.sep) and destination != target_resolved:
                        raise UploadRejectedError(
                            f"Archive entry '{filename}' attempts path traversal outside target directory."
                        )

                    if info.is_dir():
                        destination.mkdir(parents=True, exist_ok=True)
                        continue

                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info) as src, open(destination, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    file_count += 1

            # Detect root project directory (if archive was zipped with a single root directory)
            extracted_root = self.detect_project_root(temp_extract_dir)

            # Move contents to target_dir
            target_dir.mkdir(parents=True, exist_ok=True)
            for item in extracted_root.iterdir():
                dest_item = target_dir / item.name
                if dest_item.exists():
                    if dest_item.is_dir():
                        shutil.rmtree(dest_item)
                    else:
                        dest_item.unlink()
                shutil.move(str(item), str(dest_item))

            return file_count, total_uncompressed

        finally:
            shutil.rmtree(temp_extract_dir, ignore_errors=True)

    def detect_project_root(self, extract_dir: Path) -> Path:
        """If extract_dir contains a single root folder (common in GitHub ZIP downloads), unwrap it."""
        items = [i for i in extract_dir.iterdir() if i.name not in {"__MACOSX", ".DS_Store"}]
        if len(items) == 1 and items[0].is_dir():
            return items[0]
        return extract_dir


archive_engine = ArchiveEngine()
