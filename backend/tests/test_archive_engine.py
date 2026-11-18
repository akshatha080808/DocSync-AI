"""Unit and integration tests for ArchiveEngine:
- Normal extraction & project root detection
- Symlink rejection
- Path traversal (ZIP Slip) attempt rejection
- Empty file rejection
- Max size violation
"""

import io
import zipfile
from pathlib import Path
import pytest

from app.core.exceptions import UploadRejectedError
from app.engines.archive_engine import ArchiveEngine


def test_archive_engine_valid_zip(tmp_path: Path):
    zip_path = tmp_path / "valid.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("root_folder/file1.py", "print('hello')\n")
        zf.writestr("root_folder/sub/file2.js", "console.log('hi');\n")

    dest_dir = tmp_path / "extracted"
    engine = ArchiveEngine()
    count, size = engine.validate_and_extract_zip(zip_path, dest_dir)

    assert count == 2
    assert (dest_dir / "file1.py").exists()
    assert (dest_dir / "sub" / "file2.js").exists()
    assert (dest_dir / "file1.py").read_text().strip() == "print('hello')"


def test_archive_engine_empty_zip(tmp_path: Path):
    empty_file = tmp_path / "empty.zip"
    empty_file.write_bytes(b"")

    dest_dir = tmp_path / "extracted"
    engine = ArchiveEngine()
    with pytest.raises(UploadRejectedError, match="empty"):
        engine.validate_and_extract_zip(empty_file, dest_dir)


def test_archive_engine_zip_slip_prevention(tmp_path: Path):
    slip_zip = tmp_path / "slip.zip"
    with zipfile.ZipFile(slip_zip, "w") as zf:
        # Attempt traversal outside destination
        zf.writestr("../../../evil.txt", "malicious payload")

    dest_dir = tmp_path / "extracted"
    engine = ArchiveEngine()
    with pytest.raises(UploadRejectedError, match="traversal"):
        engine.validate_and_extract_zip(slip_zip, dest_dir)


def test_archive_engine_symlink_rejection(tmp_path: Path):
    symlink_zip = tmp_path / "symlink.zip"
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zinfo = zipfile.ZipInfo("symlink_target")
        # Unix symlink attribute: 0o120777 << 16
        zinfo.external_attr = 0o120777 << 16
        zf.writestr(zinfo, "/etc/passwd")

    symlink_zip.write_bytes(zip_buffer.getvalue())

    dest_dir = tmp_path / "extracted"
    engine = ArchiveEngine()
    with pytest.raises(UploadRejectedError, match="symlink"):
        engine.validate_and_extract_zip(symlink_zip, dest_dir)


def test_archive_engine_size_limits(tmp_path: Path):
    large_zip = tmp_path / "large.zip"
    with zipfile.ZipFile(large_zip, "w") as zf:
        zf.writestr("file.txt", "a" * 1000)

    dest_dir = tmp_path / "extracted"
    engine = ArchiveEngine(max_extract_bytes=500)
    with pytest.raises(UploadRejectedError, match="exceeds maximum allowed limit"):
        engine.validate_and_extract_zip(large_zip, dest_dir)
