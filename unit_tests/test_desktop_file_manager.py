"""UNIT TESTS ONLY FOR NON UI RELATED FUNCTIONALITY,
 I DONT KNOW HOW TO TEST THE UI RELATED STUFF"""


import os
import pytest
from tempfile import TemporaryDirectory, NamedTemporaryFile
from core.desktop_file_manager import (DesktopPDFFileManager,
                                        FileOperationResult,
                                        get_desktop_default_output_path, 
                                        validate_desktop_output_path,
                                        format_file_size, 
                                        create_backup_filename)

# Test data
SAMPLE_PDF = b'%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n<</Type/Page/Parent 2 0 R/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>>>>>/MediaBox[0 0 612 792]/Contents 4 0 R>>\nendobj\n4 0 obj\n<</Length 44>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Hello World) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000120 00000 n \n0000000256 00000 n \ntrailer\n<</Size 5/Root 1 0 R>>\nstartxref\n365\n%%EOF'

# ===================
# Fixtures
# ===================
@pytest.fixture
def file_manager():
    return DesktopPDFFileManager()

@pytest.fixture
def sample_pdf_file():
    with NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(SAMPLE_PDF)
        f.flush()
        yield f.name
    os.unlink(f.name)

@pytest.fixture
def text_file():
    with NamedTemporaryFile(suffix='.txt', delete=False) as f:
        f.write(b'This is a text file')
        yield f.name
    os.unlink(f.name)

# ===================
# DesktopPDFFileManager Tests
# ===================
def test_initial_state(file_manager):
    assert file_manager.get_files() == []
    assert file_manager.get_file_count() == 0

def test_add_valid_file(file_manager, sample_pdf_file):
    response = file_manager.add_files([sample_pdf_file])
    assert response.result == FileOperationResult.SUCCESS
    assert file_manager.get_files() == [sample_pdf_file]
    assert file_manager.get_file_count() == 1

def test_add_invalid_file(file_manager, text_file):
    response = file_manager.add_files([text_file])
    assert response.result == FileOperationResult.ERROR
    assert "not a PDF" in response.message
    assert file_manager.get_file_count() == 0

def test_add_nonexistent_file(file_manager):
    response = file_manager.add_files(["/nonexistent/file.pdf"])
    assert response.result == FileOperationResult.ERROR
    assert "not found" in response.message

def test_remove_file(file_manager, sample_pdf_file):
    file_manager.add_files([sample_pdf_file])
    response = file_manager.remove_file(0)
    assert response.result == FileOperationResult.SUCCESS
    assert file_manager.get_file_count() == 0

def test_clear_files(file_manager, sample_pdf_file):
    file_manager.add_files([sample_pdf_file, sample_pdf_file])
    response = file_manager.clear_files()
    assert response.result == FileOperationResult.SUCCESS
    assert "Cleared 1 file" in response.message
    assert file_manager.get_file_count() == 0


# ===================
# Utility Function Tests
# ===================
def test_get_desktop_default_output_path():
    path = get_desktop_default_output_path()
    assert path.endswith("merged_document.pdf")
    assert "Desktop" in path or os.path.expanduser("~") in path

def test_validate_output_path():
    with TemporaryDirectory() as tmpdir:
        valid_path = os.path.join(tmpdir, "test.pdf")
        response = validate_desktop_output_path(valid_path)
        assert response[0] is True
        
        # Test existing unwritable file (simulate by making dir read-only)
        os.chmod(tmpdir, 0o444)
        response = validate_desktop_output_path(valid_path)
        assert response[0] is False
        os.chmod(tmpdir, 0o755)  # Reset permissions

def test_format_file_size(sample_pdf_file):
    size = format_file_size(sample_pdf_file)
    assert "KB" in size or "B" in size
    assert "Unknown" not in size

def test_create_backup_filename(sample_pdf_file):
    backup = create_backup_filename(sample_pdf_file)
    assert backup != sample_pdf_file
    assert "_" in backup
    assert backup.endswith(".pdf")
    
    # Test with non-existent file
    assert create_backup_filename("/nonexistent/file.pdf") == "/nonexistent/file.pdf"

# ===================
# Test Runner
# ===================
if __name__ == "__main__":
    pytest.main(["-v", "test_desktop_file_manager.py"])