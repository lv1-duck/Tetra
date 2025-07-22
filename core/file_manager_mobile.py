"""
Mobile File Management Module for PDF operations
Handles file selection, validation, and PDF operations for mobile platforms (Android, iOS)
"""

import os
from typing import List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

try:
    from plyer import filechooser  # mobile file picking
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

try:
    import PyPDF2
    PDF_LIBRARY_AVAILABLE = True
except ImportError:
    PDF_LIBRARY_AVAILABLE = False


class FileOperationResult(Enum):
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class FileOperationResponse:
    result: FileOperationResult
    message: str
    data: Optional[any] = None


class MobilePDFFileManager:
    """Manages PDF file operations and maintains file list state for mobile platforms"""
    
    def __init__(self, platform: str = 'android'):
        self.selected_files: List[str] = []
        self._observers: List[Callable] = []
        self.platform = platform
    
    def add_observer(self, callback: Callable):
        """Add observer for file list changes"""
        self._observers.append(callback)
    
    def remove_observer(self, callback: Callable):
        """Remove observer"""
        if callback in self._observers:
            self._observers.remove(callback)
    
    def _notify_observers(self):
        """Notify all observers of file list changes"""
        for callback in self._observers:
            try:
                callback(self.selected_files.copy())
            except Exception as e:
                print(f"Observer notification error: {e}")
    
    def add_files(self, file_paths: List[str]) -> FileOperationResponse:
        """Add files to the selection, with validation"""
        if not file_paths:
            return FileOperationResponse(
                FileOperationResult.ERROR,
                "No files provided"
            )
        
        added_files = []
        invalid_files = []
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                invalid_files.append(f"{os.path.basename(file_path)} (not found)")
                continue
            
            if not file_path.lower().endswith('.pdf'):
                invalid_files.append(f"{os.path.basename(file_path)} (not a PDF)")
                continue
            
            if not self._is_valid_pdf(file_path):
                invalid_files.append(f"{os.path.basename(file_path)} (corrupted PDF)")
                continue
            
            if file_path not in self.selected_files:
                self.selected_files.append(file_path)
                added_files.append(os.path.basename(file_path))
        
        self._notify_observers()
        
        if added_files and not invalid_files:
            return FileOperationResponse(
                FileOperationResult.SUCCESS,
                f"Added {len(added_files)} files successfully"
            )
        elif added_files and invalid_files:
            return FileOperationResponse(
                FileOperationResult.SUCCESS,
                f"Added {len(added_files)} files. Skipped {len(invalid_files)} invalid files"
            )
        else:
            return FileOperationResponse(
                FileOperationResult.ERROR,
                f"No valid files added. Issues: {', '.join(invalid_files)}"
            )
    
    def remove_file(self, index: int) -> FileOperationResponse:
        """Remove file at specific index"""
        if not 0 <= index < len(self.selected_files):
            return FileOperationResponse(
                FileOperationResult.ERROR,
                "Invalid file index"
            )
        
        removed_file = os.path.basename(self.selected_files.pop(index))
        self._notify_observers()
        
        return FileOperationResponse(
            FileOperationResult.SUCCESS,
            f"Removed {removed_file}"
        )
    
    def clear_files(self) -> FileOperationResponse:
        """Clear all selected files"""
        count = len(self.selected_files)
        self.selected_files.clear()
        self._notify_observers()
        
        return FileOperationResponse(
            FileOperationResult.SUCCESS,
            f"Cleared {count} files"
        )
    
    def move_file(self, from_index: int, to_index: int) -> FileOperationResponse:
        """Move file from one position to another"""
        if not (0 <= from_index < len(self.selected_files) and 
                0 <= to_index < len(self.selected_files)):
            return FileOperationResponse(
                FileOperationResult.ERROR,
                "Invalid indices"
            )
        
        file_path = self.selected_files.pop(from_index)
        self.selected_files.insert(to_index, file_path)
        self._notify_observers()
        
        return FileOperationResponse(
            FileOperationResult.SUCCESS,
            "File reordered successfully"
        )
    
    def get_files(self) -> List[str]:
        """Get copy of current file list"""
        return self.selected_files.copy()
    
    def get_file_count(self) -> int:
        """Get number of selected files"""
        return len(self.selected_files)
    
    def merge_pdfs(self, output_path: str) -> FileOperationResponse:
        """Merge all selected PDFs into one file"""
        if not PDF_LIBRARY_AVAILABLE:
            return FileOperationResponse(
                FileOperationResult.ERROR,
                "PyPDF2 library not available. Install with: pip install PyPDF2"
            )
        
        if len(self.selected_files) < 2:
            return FileOperationResponse(
                FileOperationResult.ERROR,
                "Need at least 2 files to merge"
            )
        
        # Validate output path for mobile platform
        is_valid, error_msg = validate_mobile_output_path(output_path, self.platform)
        if not is_valid:
            return FileOperationResponse(
                FileOperationResult.ERROR,
                f"Invalid output path: {error_msg}"
            )
        
        try:
            merger = PyPDF2.PdfMerger()
            
            for file_path in self.selected_files:
                if not os.path.exists(file_path):
                    return FileOperationResponse(
                        FileOperationResult.ERROR,
                        f"File not found: {os.path.basename(file_path)}"
                    )
                merger.append(file_path)
            
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            with open(output_path, 'wb') as output_file:
                merger.write(output_file)
            
            merger.close()
            
            return FileOperationResponse(
                FileOperationResult.SUCCESS,
                f"Successfully merged {len(self.selected_files)} files to {os.path.basename(output_path)}"
            )
            
        except Exception as e:
            return FileOperationResponse(
                FileOperationResult.ERROR,
                f"Merge failed: {str(e)}"
            )
    
    def _is_valid_pdf(self, file_path: str) -> bool:
        if not PDF_LIBRARY_AVAILABLE:
            # Basic check without library
            try:
                with open(file_path, 'rb') as f:
                    header = f.read(4)
                    return header == b'%PDF'
            except:
                return False
        
        try:
            with open(file_path, 'rb') as f:
                PyPDF2.PdfReader(f)
            return True
        except:
            return False


# Mobile-specific file operations
def request_storage_permissions(platform: str) -> bool:
    """
    Basic storage permissions request
    Returns True if permissions are available, False otherwise
    """
    if platform == 'android':
        try:
            from android.permissions import request_permissions, Permission, check_permission  # type: ignore
            
            # Check if we already have permission
            if check_permission(Permission.WRITE_EXTERNAL_STORAGE):
                return True
            
            # Request both read and write permissions
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ])
            
            return True
            
        except ImportError:
            print("Android permissions module not available - running in fallback mode")
            return False
        except Exception as e:
            print(f"Error requesting Android permissions: {e}")
            return False
    
    elif platform == 'ios':
        # iOS typically handles permissions through the system
        return True
    
    else:
        # Other platforms don't need special storage permissions
        return True


def request_storage_permissions_enhanced(platform: str) -> bool:
    """
    Enhanced storage permissions request with better error handling
    Returns True if permissions are available, False otherwise
    """
    if platform == 'android':
        try:
            from android.permissions import request_permissions, Permission, check_permission  # type: ignore
            
            # List of permissions we need
            required_permissions = [
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ]
            
            # Check if we already have all permissions
            all_granted = all(check_permission(perm) for perm in required_permissions)
            if all_granted:
                print("All storage permissions already granted")
                return True
            
            # Request missing permissions
            print("Requesting storage permissions...")
            request_permissions(required_permissions)
            
            return True
            
        except ImportError:
            print("Android permissions module not available")
            return False
        except Exception as e:
            print(f"Error requesting Android permissions: {e}")
            return False
    
    elif platform == 'ios':
        print("iOS platform detected - using system permission handling")
        return True
    
    else:
        print(f"Platform {platform} - no explicit permissions needed")
        return True


def get_android_downloads_dir() -> Optional[str]:
    """Get Android Downloads directory path"""
    try:
        # Try different common Android paths
        possible_paths = [
            "/storage/emulated/0/Download",
            "/storage/emulated/0/Downloads", 
            "/sdcard/Download",
            "/sdcard/Downloads"
        ]
        
        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.W_OK):
                return path
        
        # Fallback: try to use Android-specific API
        try:
            from android.storage import primary_external_storage_path  # type: ignore
            downloads_path = os.path.join(primary_external_storage_path(), "Download")
            if os.path.exists(downloads_path):
                return downloads_path
        except ImportError:
            pass
        
        return None
    except Exception as e:
        print(f"Error getting Android downloads directory: {e}")
        return None


def get_ios_documents_dir() -> Optional[str]:
    """Get iOS app documents directory path"""
    try:
        # On iOS, typically save to the app's Documents directory
        documents_path = os.path.expanduser("~/Documents")
        if os.path.exists(documents_path):
            return documents_path
        return None
    except Exception as e:
        print(f"Error getting iOS documents directory: {e}")
        return None


def choose_directory_mobile(platform: str) -> Optional[str]:
    """Mobile directory chooser using plyer"""
    if not PLYER_AVAILABLE:
        print("plyer not available for mobile directory selection")
        return None
    
    try:
        directory = filechooser.choose_dir(title="Select Directory")
        return directory[0] if directory else None
    except Exception as e:
        print(f"Directory selection failed: {e}")
        return None


def pick_files_mobile(callback: Callable[[List[str]], None], platform: str):
    """
    Basic mobile file picking function
    """
    if not PLYER_AVAILABLE:
        print("plyer not available for mobile file picking")
        callback([])
        return
    
    if platform not in ['android', 'ios']:
        print(f"Platform {platform} not supported for mobile file picking")
        callback([])
        return
    
    # Request permissions first
    if not request_storage_permissions(platform):
        print("Storage permissions not available")
    
    try:
        files = filechooser.open_file(
            title="Select PDF Files",
            filters=[('PDF files', '*.pdf'), ('All files', '*.*')],
            multiple=True
        )
        
        if files:
            # Validate that all selected files are PDFs and exist
            valid_files = []
            for file_path in files:
                if os.path.exists(file_path) and file_path.lower().endswith('.pdf'):
                    valid_files.append(file_path)
                else:
                    print(f"Skipping invalid file: {file_path}")
            
            callback(valid_files)
        else:
            print("No files selected")
            callback([])
            
    except Exception as e:
        print(f"Mobile file picker error: {e}")
        callback([])


def pick_files_mobile_enhanced(callback: Callable[[List[str]], None], platform: str):
    """
    Enhanced mobile file picking with comprehensive error handling and permission management
    """
    if not PLYER_AVAILABLE:
        print("plyer not available for mobile file picking")
        callback([])
        return
    
    if platform not in ['android', 'ios']:
        print(f"Platform {platform} not supported for mobile file picking")
        callback([])
        return
    
    # Request permissions first with enhanced error handling
    if not request_storage_permissions_enhanced(platform):
        print("Storage permissions not available - attempting fallback")
    
    try:
        files = filechooser.open_file(
            title="Select PDF Files",
            filters=[('PDF files', '*.pdf'), ('All files', '*.*')],
            multiple=True
        )
        
        if files:
            # Validate that all selected files are PDFs and exist
            valid_files = []
            for file_path in files:
                if os.path.exists(file_path) and file_path.lower().endswith('.pdf'):
                    valid_files.append(file_path)
                else:
                    print(f"Skipping invalid file: {file_path}")
            
            callback(valid_files)
        else:
            print("No files selected")
            callback([])
            
    except Exception as e:
        print(f"Mobile file picker error: {e}")
        callback([])


def save_file_dialog_mobile(default_filename: str = "merged_document.pdf", platform: str = "android") -> Optional[str]:
    """
    Mobile save dialog using plyer
    Returns the full path where user wants to save the file, or None if cancelled
    """
    if not PLYER_AVAILABLE:
        print("plyer not available for mobile save dialog")
        return None
    
    try:
        if platform == 'android':
            # Request storage permissions first
            if not request_storage_permissions(platform):
                print("Storage permissions not available")
                return None
            
            # On Android, let user choose directory first
            try:
                directories = filechooser.choose_dir(title="Choose Save Location")
                
                if directories and directories[0]:
                    chosen_dir = directories[0]
                    return os.path.join(chosen_dir, default_filename)
                else:
                    # Fallback to default Downloads directory
                    downloads_dir = get_android_downloads_dir()
                    return os.path.join(downloads_dir, default_filename) if downloads_dir else None
                    
            except Exception as e:
                print(f"Android directory chooser failed: {e}")
                # Fallback to default location
                downloads_dir = get_android_downloads_dir()
                return os.path.join(downloads_dir, default_filename) if downloads_dir else None
        
        elif platform == 'ios':
            # iOS has different file access patterns
            try:
                documents_dir = get_ios_documents_dir()
                return os.path.join(documents_dir, default_filename) if documents_dir else None
            except Exception as e:
                print(f"iOS save location error: {e}")
                return None
        
        else:
            print(f"Unsupported mobile platform: {platform}")
            return None
            
    except Exception as e:
        print(f"Mobile save dialog error: {e}")
        return None


def get_mobile_default_output_path(platform: str) -> str:
    """Get default output path for merged PDF on mobile"""
    if platform == 'android':
        downloads_dir = get_android_downloads_dir()
        return os.path.join(downloads_dir, "merged_document.pdf") if downloads_dir else "/sdcard/merged_document.pdf"
    
    elif platform == 'ios':
        documents_dir = get_ios_documents_dir()
        return os.path.join(documents_dir, "merged_document.pdf") if documents_dir else "~/Documents/merged_document.pdf"
    
    else:
        return "merged_document.pdf"


def get_mobile_safe_path(platform: str) -> str:
    """Get a mobile-appropriate safe path for file operations"""
    try:
        if platform == 'android':
            # Try multiple Android paths in order of preference
            android_paths = [
                get_android_downloads_dir(),
                "/storage/emulated/0/Documents",
                "/sdcard/Documents"]
    except Exception as e:
        print(f"Error getting Android safe path: {e}")
        return "/sdcard/Documents"      

def validate_mobile_output_path(output_path, platform):
    """
    Validate output path for mobile platforms
    Returns (is_valid: bool, error_message: str)
    """
    if platform == 'android':
        # Check if the path is writable
        if not os.path.exists(output_path):
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            except Exception as e:
                return False, f"Failed to create directory: {e}"
        
        if not os.access(os.path.dirname(output_path), os.W_OK):
            return False, "Output directory is not writable"
        
        return True, ""
    
    elif platform == 'ios':
        # iOS typically allows writing to app's Documents directory
        if not os.path.exists(output_path):
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            except Exception as e:
                return False, f"Failed to create directory: {e}"
        
        return True, ""
    
    else:
        return False, "Unsupported platform for output validation" 