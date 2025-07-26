"""UNIT TESTS ONLY FOR NON UI RELATED FUNCTIONALITY,
 I DONT KNOW HOW TO TEST THE UI RELATED STUFF"""


import os
import pytest
from tempfile import TemporaryDirectory, NamedTemporaryFile
from unittest.mock import patch, Mock
import sys

# Mock Kivy and UI dependencies before importing
sys.modules['kivy'] = Mock()
sys.modules['kivy.utils'] = Mock()
sys.modules['kivy.metrics'] = Mock()
sys.modules['kivy.uix'] = Mock()
sys.modules['kivy.uix.popup'] = Mock()
sys.modules['kivy.uix.boxlayout'] = Mock()
sys.modules['kivy.uix.button'] = Mock()
sys.modules['kivy.uix.textinput'] = Mock()
sys.modules['kivy.uix.filechooser'] = Mock()
sys.modules['kivy.uix.label'] = Mock()
sys.modules['kivy.uix.scrollview'] = Mock()
sys.modules['ui'] = Mock()
sys.modules['ui.status_popup'] = Mock()

# Set platform for testing
with patch('kivy.utils.platform', 'linux'):
    from core.mobile_file_manager import (DesktopPDFFileManager,
                                     FileOperationResult,
                                     get_desktop_default_output_path, 
                                     validate_desktop_output_path,
                                     format_file_size, 
                                     create_backup_filename,
                                     get_mobile_documents_path,
                                     get_mobile_output_path,
                                     get_available_storage_space,
                                     format_file_size_mobile_bytes)

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
# DesktopPDFFileManager Tests (Mobile Version)
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
    assert "not PDF" in response.message
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

def test_remove_invalid_index(file_manager):
    response = file_manager.remove_file(0)
    assert response.result == FileOperationResult.ERROR
    assert "Invalid selection" in response.message

def test_clear_files(file_manager, sample_pdf_file):
    file_manager.add_files([sample_pdf_file])
    response = file_manager.clear_files()
    assert response.result == FileOperationResult.SUCCESS
    assert "Cleared 1 files" in response.message
    assert file_manager.get_file_count() == 0

def test_move_file(file_manager, sample_pdf_file):
    # Create two temporary PDF files
    with NamedTemporaryFile(suffix='.pdf', delete=False) as f2:
        f2.write(SAMPLE_PDF)
        f2.flush()
        second_pdf = f2.name
    
    try:
        file_manager.add_files([sample_pdf_file, second_pdf])
        response = file_manager.move_file(0, 1)
        assert response.result == FileOperationResult.SUCCESS
        assert "reordered" in response.message
    finally:
        os.unlink(second_pdf)

def test_move_file_invalid_indices(file_manager, sample_pdf_file):
    file_manager.add_files([sample_pdf_file])
    response = file_manager.move_file(0, 5)
    assert response.result == FileOperationResult.ERROR
    assert "Invalid selection" in response.message

def test_has_file_access(file_manager, sample_pdf_file):
    # Should have access to existing file
    assert file_manager._has_file_access(sample_pdf_file) is True
    
    # Should not have access to non-existent file
    assert file_manager._has_file_access('/fake/file.pdf') is False

def test_has_write_access(file_manager):
    with TemporaryDirectory() as tmpdir:
        # Should have write access to temp directory
        assert file_manager._has_write_access(tmpdir) is True
        
        # Should not have write access to fake directory
        assert file_manager._has_write_access('/fake/directory') is False

def test_merge_pdfs_insufficient_files(file_manager):
    response = file_manager.merge_pdfs('/fake/output.pdf')
    assert response.result == FileOperationResult.ERROR
    assert "Select at least 2 PDFs" in response.message

@patch('core.mobile_file_manager.PDF_LIBRARY_AVAILABLE', False)
def test_merge_pdfs_no_library(file_manager):
    response = file_manager.merge_pdfs('/fake/output.pdf')
    assert response.result == FileOperationResult.ERROR
    assert "PDF library not available" in response.message

def test_permission_denied_scenario(file_manager, sample_pdf_file):
    file_manager.add_files([sample_pdf_file])
    
    with patch.object(file_manager, '_has_write_access', return_value=False):
        response = file_manager.merge_pdfs('/fake/output.pdf')
        assert response.result == FileOperationResult.PERMISSION_DENIED
        assert "No write permission" in response.message

# ===================
# Mobile-Specific Utility Function Tests
# ===================
def test_get_desktop_default_output_path():
    path = get_desktop_default_output_path()
    assert path.endswith("merged_document.pdf")
    assert isinstance(path, str)

@patch('kivy.utils.platform', 'android')
@patch('core.mobile_file_manager.ANDROID_AVAILABLE', True)
def test_get_mobile_documents_path_android():
    from unittest.mock import MagicMock
    mock_storage = MagicMock()
    mock_storage.primary_external_storage_path.return_value = '/sdcard'
    
    with patch('core.mobile_file_manager.android_storage', mock_storage):
        with patch('os.path.exists', return_value=True):
            path = get_mobile_documents_path()
            assert path == '/sdcard/Documents'

@patch('kivy.utils.platform', 'ios')
def test_get_mobile_documents_path_ios():
    with patch('os.path.expanduser', return_value='/Users/test/Documents'):
        path = get_mobile_documents_path()
        assert path == '/Users/test/Documents'

@patch('kivy.utils.platform', 'android')
@patch('core.mobile_file_manager.ANDROID_AVAILABLE', True)
def test_get_mobile_output_path_android():
    from unittest.mock import MagicMock
    mock_storage = MagicMock()
    mock_storage.primary_external_storage_path.return_value = '/sdcard'
    
    with patch('core.mobile_file_manager.android_storage', mock_storage):
        with patch('os.path.exists', return_value=True):
            path = get_mobile_output_path()
            assert path == '/sdcard/Download'

def test_validate_output_path():
    with TemporaryDirectory() as tmpdir:
        valid_path = os.path.join(tmpdir, "test.pdf")
        is_valid, message = validate_desktop_output_path(valid_path)
        assert is_valid is True
        assert "valid" in message.lower()
        
        # Test directory without write permission
        os.chmod(tmpdir, 0o444)
        is_valid, message = validate_desktop_output_path(valid_path)
        assert is_valid is False
        assert "permission" in message.lower()
        os.chmod(tmpdir, 0o755)  # Reset permissions

def test_format_file_size(sample_pdf_file):
    size = format_file_size(sample_pdf_file)
    assert any(unit in size for unit in ['B', 'KB', 'MB', 'GB'])
    assert "???" not in size

def test_format_file_size_nonexistent():
    size = format_file_size("/nonexistent/file.pdf")
    assert size == "???"

def test_format_file_size_mobile_bytes():
    assert format_file_size_mobile_bytes(500) == "0KB"
    assert format_file_size_mobile_bytes(1024) == "1KB"
    assert format_file_size_mobile_bytes(1024 * 1024) == "1MB"
    assert format_file_size_mobile_bytes(1024 * 1024 * 1024) == "1.0GB"

def test_create_backup_filename(sample_pdf_file):
    backup = create_backup_filename(sample_pdf_file)
    assert backup != sample_pdf_file
    assert "_" in backup
    assert backup.endswith(".pdf")
    
    # Test with non-existent file
    assert create_backup_filename("/nonexistent/file.pdf") == "/nonexistent/file.pdf"

@patch('shutil.disk_usage')
def test_get_available_storage_space(mock_disk_usage):
    # Mock disk usage: total, used, free (500MB free)
    mock_disk_usage.return_value = (1000000000, 500000000, 500000000)
    
    with patch('core.mobile_file_manager.get_mobile_output_path', return_value='/test'):
        space = get_available_storage_space()
        assert any(unit in space for unit in ['KB', 'MB', 'GB'])

def test_get_available_storage_space_error():
    with patch('core.mobile_file_manager.get_mobile_output_path', side_effect=Exception()):
        space = get_available_storage_space()
        assert space == "Unknown"

# ===================
# Observer Pattern Tests
# ===================
def test_observer_management(file_manager):
    from unittest.mock import MagicMock
    callback1 = MagicMock()
    callback2 = MagicMock()
    
    # Add observers
    file_manager.add_observer(callback1)
    file_manager.add_observer(callback2)
    assert len(file_manager._file_list_observers) == 2
    
    # Remove observer
    file_manager.remove_observer(callback1)
    assert len(file_manager._file_list_observers) == 1
    assert callback2 in file_manager._file_list_observers

def test_observer_notification(file_manager, sample_pdf_file):
    from unittest.mock import MagicMock
    callback = MagicMock()
    file_manager.add_observer(callback)
    
    # Adding files should trigger notification
    file_manager.add_files([sample_pdf_file])
    callback.assert_called_once()

# ===================
# Test Runner
# ===================
if __name__ == "__main__":
    pytest.main(["-v", "test_core.mobile_file_manager.py"])