"""
Desktop File Management Module for PDF operations
Handles file selection, validation, and PDF operations for desktop platforms (Windows, macOS, Linux)
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


class DesktopPDFFileManager:
    """Manages PDF file operations and maintains file list state for desktop platforms"""
    
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


# Desktop-specific file picking functions
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


def choose_directory_desktop() -> Optional[str]:
    """Desktop directory chooser using tkinter"""
    try:
        from tkinter import filedialog
        import tkinter as tk
        
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        directory = filedialog.askdirectory(title="Select Directory")
        root.destroy()
        return directory if directory else None
        
    except ImportError:
        print("tkinter not available for directory picker")
        return None


def save_file_dialog_desktop(default_filename: str = "merged_document.pdf") -> Optional[str]:
    """
    Desktop save dialog using tkinter
    Returns the full path where user wants to save the file, or None if cancelled
    """
    try:
        from tkinter import filedialog
        import tkinter as tk
        
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        # Show save dialog with default filename
        file_path = filedialog.asksaveasfilename(
            title="Save Merged PDF As...",
            defaultextension=".pdf",
            filetypes=[
                ("PDF files", "*.pdf"),
                ("All files", "*.*")
            ],
            initialvalue=default_filename
        )
        
        root.destroy()
        return file_path if file_path else None
        
    except ImportError:
        print("tkinter not available for save dialog")
        return None
    except Exception as e:
        print(f"Desktop save dialog error: {e}")
        return None


def get_desktop_default_output_path() -> str:
    """Get default output path for merged PDF on desktop"""
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.path.exists(desktop):
        return os.path.join(desktop, "merged_document.pdf")
    else:
        return os.path.join(os.path.expanduser("~"), "merged_document.pdf")


def get_desktop_safe_path() -> str:
    """Get a desktop-appropriate safe path for file operations"""
    desktop_paths = [
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.path.expanduser("~"), "Documents"),
        os.path.expanduser("~"),
        os.getcwd()
    ]
    
    for path in desktop_paths:
        if os.path.exists(path) and os.access(path, os.W_OK):
            return path
    
    # Ultimate fallback
    return os.getcwd()


def validate_desktop_output_path(output_path: str) -> tuple[bool, str]:
    """
    Validate if the output path is writable on desktop platforms
    Returns (is_valid, error_message)
    """
    try:
        # Check if path exists
        if not os.path.exists(output_path):
            # Try to create the directory
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            except Exception as e:
                return False, f"Cannot create directory: {e}"
        
        # Check if we can write to the location
        directory = os.path.dirname(output_path)
        if not os.access(directory, os.W_OK):
            return False, f"No write permission for directory: {directory}"
        
        # Check if file already exists and is writable
        if os.path.exists(output_path):
            if not os.access(output_path, os.W_OK):
                return False, f"File exists but is not writable: {output_path}"
        
        return True, "Path is valid"
    
    except Exception as e:
        return False, f"Path validation error: {e}"


def format_file_size(file_path: str) -> str:
    """Format file size in human readable format"""
    try:
        size = os.path.getsize(file_path)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return "Massive file size"
    except:
        return "Unknown size"


def create_backup_filename(original_path: str) -> str:
    """
    Create a backup filename if the original already exists
    Returns a new filename with timestamp or counter
    """
    if not os.path.exists(original_path):
        return original_path
    
    directory = os.path.dirname(original_path)
    filename = os.path.basename(original_path)
    name, ext = os.path.splitext(filename)
    
    # Try with timestamp first
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(directory, f"{name}_{timestamp}{ext}")
    
    if not os.path.exists(backup_path):
        return backup_path
    
    # If timestamp version exists, use counter
    counter = 1
    while True:
        backup_path = os.path.join(directory, f"{name}_{counter:03d}{ext}")
        if not os.path.exists(backup_path):
            return backup_path
        counter += 1
        if counter > 999:  # Safety limit
            break
    
    return original_path  # Fallback to original