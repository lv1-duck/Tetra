"""
Mobile File Management Module for PDF operations
Handles file selection, validation, and PDF operations for mobile platforms (Android, iOS)
"""

# IMPORTS AND DEPENDENCIES
import os
from typing import List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

try:
    from plyer import filechooser  # MOBILE FILE PICKING
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

try:
    import PyPDF2
    PDF_LIBRARY_AVAILABLE = True
except ImportError:
    PDF_LIBRARY_AVAILABLE = False


# ENUM FOR FILE OPERATION RESULTS
class FileOperationResult(Enum):
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


# DATACLASS FOR FILE OPERATION RESPONSE
@dataclass
class FileOperationResponse:
    result: FileOperationResult
    message: str
    data: Optional[any] = None


# MANAGES PDF FILE OPERATIONS AND MAINTAINS FILE LIST STATE FOR MOBILE PLATFORMS
class MobilePDFFileManager:
    # INITIALIZE MANAGER WITH PLATFORM AND OBSERVERS
    def __init__(self, platform: str = 'android'):
        self.selected_files: List[str] = []
        self._observers: List[Callable] = []
        self.platform = platform
    
    # ADD OBSERVER FOR FILE LIST CHANGES
    def add_observer(self, callback: Callable):
        self._observers.append(callback)
    
    # REMOVE OBSERVER
    def remove_observer(self, callback: Callable):
        if callback in self._observers:
            self._observers.remove(callback)
    
    # NOTIFY ALL OBSERVERS OF FILE LIST CHANGES
    def _notify_observers(self):
        for callback in self._observers:
            try:
                callback(self.selected_files.copy())
            except Exception as e:
                print(f"Observer notification error: {e}")
    
    # ADD FILES TO THE SELECTION WITH VALIDATION
    def add_files(self, file_paths: List[str]) -> FileOperationResponse:
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
    
    # REMOVE FILE AT SPECIFIC INDEX
    def remove_file(self, index: int) -> FileOperationResponse:
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
    
    # CLEAR ALL SELECTED FILES
    def clear_files(self) -> FileOperationResponse:
        count = len(self.selected_files)
        self.selected_files.clear()
        self._notify_observers()
        
        return FileOperationResponse(
            FileOperationResult.SUCCESS,
            f"Cleared {count} files"
        )
    
    # MOVE FILE FROM ONE POSITION TO ANOTHER
    def move_file(self, from_index: int, to_index: int) -> FileOperationResponse:
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
    
    # GET COPY OF CURRENT FILE LIST
    def get_files(self) -> List[str]:
        return self.selected_files.copy()
    
    # GET NUMBER OF SELECTED FILES
    def get_file_count(self) -> int:
        return len(self.selected_files)
    
    # MERGE ALL SELECTED PDFS INTO ONE FILE
    def merge_pdfs(self, output_path: str) -> FileOperationResponse:
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
    
    # BASIC PDF VALIDATION CHECK
    def _is_valid_pdf(self, file_path: str) -> bool:
        if not PDF_LIBRARY_AVAILABLE:
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


# STORAGE PERMISSIONS REQUEST
def request_storage_permissions(platform: str) -> bool:
    if platform == 'android':
        try:
            from android.permissions import request_permissions, Permission, check_permission  # type: ignore
            
            required_permissions = [
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ]
            
            all_granted = all(check_permission(perm) for perm in required_permissions)
            if all_granted:
                return True
            
            request_permissions(required_permissions)
            
            return True
            
        except ImportError:
            print("Android permissions module not available")
            return False
        except Exception as e:
            print(f"Error requesting Android permissions: {e}")
            return False
    
    elif platform == 'ios':
        print("IOS PLATFORM DETECTED - USING SYSTEM PERMISSION HANDLING")
        return True
    
    else:
        print(f"PLATFORM {platform} - NO EXPLICIT PERMISSIONS NEEDED")
        return True

# GET AND RETURN ANDROID DOWNLOADS DIRECTORY PATH
def get_android_downloads_dir() -> Optional[str]:
    try:
        possible_paths = [
            "/storage/emulated/0/Download",
            "/storage/emulated/0/Downloads", 
            "/sdcard/Download",
            "/sdcard/Downloads"
        ]
        
        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.W_OK):
                return path
        
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

# GET IOS APP DOCUMENTS DIRECTORY PATH
def get_ios_documents_dir() -> Optional[str]:
    try:
        documents_path = os.path.expanduser("~/Documents")
        if os.path.exists(documents_path):
            return documents_path
        return None
    except Exception as e:
        print(f"Error getting IOS documents directory: {e}")
        return None

# MOBILE DIRECTORY CHOOSER USING PLYER
def choose_directory_mobile(platform: str) -> Optional[str]:
    if not PLYER_AVAILABLE:
        print("PLYER NOT AVAILABLE FOR MOBILE DIRECTORY SELECTION")
        return None
    
    try:
        directory = filechooser.choose_dir(title="Select Directory")
        return directory[0] if directory else None
    except Exception as e:
        print(f"Directory selection failed: {e}")
        return None


# MOBILE FILE PICKER USING PLYER
def pick_files(callback: Callable[[List[str]], None], platform: str):
    if not PLYER_AVAILABLE:
        print("Plyer not available for file picking")
        callback([])
        return
    
    if platform not in ['android', 'ios']:
        print(f"{platform} not supported for mobile file picking")
        callback([])
        return
    
    try:
        files = filechooser.open_file(
            title="Select PDF Files",
            filters=[('PDF files', '*.pdf'), ('All files', '*.*')],
            multiple=True
        )
        
        if files:
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
        print(f"Mobile File Picker Error: {e}")
        callback([])

# MOBILE SAVE DIALOG USING PLYER
def save_file_dialog_mobile(default_filename: str = "merged_document.pdf", platform: str = "android") -> Optional[str]:
    if not PLYER_AVAILABLE:
        print("Plyer not available for mobile file saving")
        return None

    try:
        if platform == 'android':
            if not request_storage_permissions(platform):
                print("Storage permissions not granted, cannot save file")
                return None
            
            try:
                directories = filechooser.choose_dir(title="Choose Save Location")
                
                if directories and directories[0]:
                    chosen_dir = directories[0]
                    return os.path.join(chosen_dir, default_filename)
                else:
                    downloads_dir = get_android_downloads_dir()
                    return os.path.join(downloads_dir, default_filename) if downloads_dir else None
                    
            except Exception as e:
                print(f"Android Directory Chooser Failed: {e}")
                downloads_dir = get_android_downloads_dir()
                return os.path.join(downloads_dir, default_filename) if downloads_dir else None
        
        elif platform == 'ios':
            pass  #I STILL DO NOT KNOW HOW TO HANDLE IOS FILE SAVING,
        
        else:
            print(f"Unsupported Mobile Platform: {platform}")
            return None
            
    except Exception as e:
        print(f"File Save Error: {e}")
        return None

# GET DEFAULT OUTPUT PATH FOR MERGED PDF ON MOBILE
def get_mobile_default_output_path(platform: str) -> str:
    if platform == 'android':
        downloads_dir = get_android_downloads_dir()
        return os.path.join(downloads_dir, "merged_document.pdf") if downloads_dir else "/sdcard/merged_document.pdf"
    
    elif platform == 'ios':
        documents_dir = get_ios_documents_dir()
        return os.path.join(documents_dir, "merged_document.pdf") if documents_dir else "~/Documents/merged_document.pdf"
    
    else:
        return "merged_document.pdf"

# VALIDATE OUTPUT PATH FOR MOBILE PLATFORMS
def validate_mobile_output_path(output_path, platform):
    if platform == 'android':
        if not os.path.exists(output_path):
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            except Exception as e:
                return False, f"Failed to create directory: {e}"
        
        if not os.access(os.path.dirname(output_path), os.W_OK):
            return False, "Output directory is not writable"
        
        return True, ""
    
    elif platform == 'ios':
        if not os.path.exists(output_path):
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            except Exception as e:
                return False, f"Failed to create directory: {e}"
        
        return True, ""
    
    else:
        return False, "Unsupported platform for output validation"
