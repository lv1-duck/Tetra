"""
File management module for PDF operations
Handles file selection, validation, and PDF operations
"""

import os
from typing import List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

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


class PDFFileManager:
    """Manages PDF file operations and maintains file list state"""
    
    def __init__(self):
        self.selected_files: List[str] = []
        self._observers: List[Callable] = []
    
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
        """Check if file is a valid PDF"""
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


# Platform-specific file picking functions
def pick_files_desktop(callback: Callable[[List[str]], None]):
    """Desktop file picker using tkinter"""
    try:
        from tkinter import filedialog
        import tkinter as tk
        
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        files = filedialog.askopenfilenames(
            title="Select PDF Files",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        root.destroy()
        callback(list(files) if files else [])
        
    except ImportError:
        print("tkinter not available for file picker")
        callback([])


def request_storage_permissions(platform: str):
    if platform == 'android':
        from android.permissions import request_permissions, Permission # type: ignore
        request_permissions([Permission.READ_EXTERNAL_STORAGE])
    elif platform == 'ios':
        # TODO: handle iOS or desktop cases if needed 
        pass
    else:
        # For desktop platforms, no permissions are needed
        pass


def pick_files_mobile(callback: Callable[[List[str]], None], platform: str):
    """Mobile file picker - placeholder implementation"""
    # This would need platform-specific implementation
    # For now, just a placeholder
    print(f"Mobile file picker not implemented for {platform}")
    callback([])


# Utility functions
def get_default_output_path() -> str:
    """Get default output path for merged PDF"""
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.path.exists(desktop):
        return os.path.join(desktop, "merged_document.pdf")
    else:
        return os.path.join(os.path.expanduser("~"), "merged_document.pdf")


def format_file_size(file_path: str) -> str:
    """Get human-readable file size"""
    try:
        size = os.path.getsize(file_path)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    except:
        return "Unknown size"