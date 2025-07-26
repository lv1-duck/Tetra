"""
Mobile File Management Module for PDF operations
Handles file selection, validation, and PDF operations for mobile platforms (Android, iOS)
Optimized for touch interfaces and mobile file system patterns.
"""

import os
from typing import List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from ui.status_popup import StatusPopup

# PDF library availability check
try:
    import fitz
    PDF_LIBRARY_AVAILABLE = True
except ImportError:
    PDF_LIBRARY_AVAILABLE = False

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserIconView  # Icon view better for mobile
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp, sp
from kivy.utils import platform


# Mobile-specific imports
if platform == 'android':
    try:
        from android.permissions import request_permissions, Permission # type: ignore
        from android.storage import primary_external_storage_path, secondary_external_storage_path # type: ignore
        ANDROID_AVAILABLE = True
        
    except ImportError:
        ANDROID_AVAILABLE = False
else:
    ANDROID_AVAILABLE = False

# FILE OPERATION RESULTS CLASS
class FileOperationResult(Enum):
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"
    PERMISSION_DENIED = "permission_denied"

@dataclass
class FileOperationResponse:
    result: FileOperationResult
    message: str
    data: Optional[Any] = None

class MobilePDFFileManager:
    """Manages PDF file operations and maintains file list state for mobile platforms"""
    def __init__(self):
        self.selected_files: List[str] = []
        self._file_list_observers: List[Callable] = []
        self._request_mobile_permissions()

    def _request_mobile_permissions(self):
        """Request necessary permissions for mobile platforms"""
        if platform == 'android' and ANDROID_AVAILABLE:
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ])

    def add_observer(self, callback: Callable):
        """Register callback for file list changes"""
        self._file_list_observers.append(callback)

    def remove_observer(self, callback: Callable):
        """Unregister file list change callback"""
        if callback in self._file_list_observers:
            self._file_list_observers.remove(callback)

    def _notify_file_list_observers(self):
        """Notify all observers about file list changes"""
        for callback in self._file_list_observers:
            try:
                callback(self.selected_files.copy())
            except Exception as error:
                print(f"Observer notification error: {error}")

    def add_files(self, file_paths: List[str]) -> FileOperationResponse:
        """Add valid PDF files to selected files list"""
        if not file_paths:
            return FileOperationResponse(FileOperationResult.ERROR, "No files selected")

        added_files = []
        invalid_files = []
        
        for path in file_paths:
            file_name = os.path.basename(path)
            
            if not os.path.exists(path):
                invalid_files.append(f"{file_name} (not found)")
            elif not self._has_file_access(path):
                invalid_files.append(f"{file_name} (no permission)")
            elif not path.lower().endswith('.pdf'):
                invalid_files.append(f"{file_name} (not PDF)")
            elif not self._is_valid_pdf(path):
                invalid_files.append(f"{file_name} (corrupted)")
            elif path in self.selected_files:
                invalid_files.append(f"{file_name} (already added)")
            else:
                self.selected_files.append(path)
                added_files.append(file_name)

        if added_files:
            self._notify_file_list_observers()
        
        # Generate response messages
        if added_files and not invalid_files:
            return FileOperationResponse(
                FileOperationResult.SUCCESS, 
                f"Added {len(added_files)} files"
            )
        if added_files and invalid_files:
            return FileOperationResponse(
                FileOperationResult.SUCCESS, 
                f"Added {len(added_files)} files\nSkipped {len(invalid_files)} invalid files"
            )
        return FileOperationResponse(
            FileOperationResult.ERROR, 
            f"No valid files added\n{'; '.join(invalid_files)}"
        )

    def remove_file(self, index: int) -> FileOperationResponse:
        """Remove file from selected files list by index"""
        if not (0 <= index < len(self.selected_files)):
            return FileOperationResponse(FileOperationResult.ERROR, "Invalid selection")
        
        removed_file_name = os.path.basename(self.selected_files.pop(index))
        self._notify_file_list_observers()
        
        return FileOperationResponse(
            FileOperationResult.SUCCESS, 
            f"Removed {removed_file_name}"
        )

    def clear_files(self) -> FileOperationResponse:
        """Clear all files from selected files list"""
        file_count = len(self.selected_files)
        self.selected_files.clear()
        self._notify_file_list_observers()
        return FileOperationResponse(
            FileOperationResult.SUCCESS, 
            f"Cleared {file_count} files"
        )

    def move_file(self, from_index: int, to_index: int) -> FileOperationResponse:
        """Move file to new position in selected files list"""
        if not (0 <= from_index < len(self.selected_files)) or not (0 <= to_index < len(self.selected_files)):
            return FileOperationResponse(FileOperationResult.ERROR, "Invalid selection")
        
        file_to_move = self.selected_files.pop(from_index)
        self.selected_files.insert(to_index, file_to_move)
        self._notify_file_list_observers()
        
        return FileOperationResponse(FileOperationResult.SUCCESS, "Files reordered")

    def get_files(self) -> List[str]:
        """Get copy of selected files list"""
        return self.selected_files.copy()

    def get_file_count(self) -> int:
        """Get number of selected files"""
        return len(self.selected_files)
    
    def merge_pdfs(self, output_path: str) -> FileOperationResponse:
        """Merge selected PDF files into single output file"""
        if not PDF_LIBRARY_AVAILABLE:
            return FileOperationResponse(
                FileOperationResult.ERROR, 
                "PDF library not available\nInstall PyMuPDF to enable merging"
            )
        if len(self.selected_files) < 2:
            return FileOperationResponse(
                FileOperationResult.ERROR, 
                "Select at least 2 PDFs to merge"
            )
        
        if not self._has_write_access(os.path.dirname(output_path)):
            return FileOperationResponse(
                FileOperationResult.PERMISSION_DENIED,
                "No write permission for output location"
            )
        
        try:
            # Create a new PDF document
            pdf_merger = fitz.open()
            
            for file_path in self.selected_files:
                if not os.path.exists(file_path):
                    pdf_merger.close()
                    return FileOperationResponse(
                        FileOperationResult.ERROR, 
                        f"File missing: {os.path.basename(file_path)}"
                    )
                
                if not self._has_file_access(file_path):
                    pdf_merger.close()
                    return FileOperationResponse(
                        FileOperationResult.PERMISSION_DENIED,
                        f"No access to: {os.path.basename(file_path)}"
                    )
                
                # Open source PDF and insert all pages
                source_pdf = fitz.open(file_path)
                pdf_merger.insert_pdf(source_pdf)
                source_pdf.close()
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save the merged PDF
            pdf_merger.save(output_path)
            pdf_merger.close()
            
            return FileOperationResponse(
                FileOperationResult.SUCCESS, 
                f"Successfully merged {len(self.selected_files)} PDFs"
            )
        except PermissionError:
            return FileOperationResponse(
                FileOperationResult.PERMISSION_DENIED,
                "Permission denied accessing files"
            )
        except Exception as error:
            return FileOperationResponse(
                FileOperationResult.ERROR, 
                f"Merge failed: {str(error)}"
            )

    def _is_valid_pdf(self, path: str) -> bool:
        """Check if file is a valid PDF"""
        if not self._has_file_access(path):
            return False
            
        if PDF_LIBRARY_AVAILABLE:
            try:
                doc = fitz.open(path)
                is_pdf = doc.is_pdf
                doc.close()
                return is_pdf
            except:
                return False
        else:
            try:
                with open(path, 'rb') as file:
                    return file.read(4) == b'%PDF'
            except:
                return False

    def _has_file_access(self, path: str) -> bool:
        """Check if we have read access to file"""
        try:
            return os.access(path, os.R_OK)
        except:
            return False

    def _has_write_access(self, path: str) -> bool:
        """Check if we have write access to directory"""
        try:
            return os.access(path, os.W_OK)
        except:
            return False

# MOBILE FILE PICKER FUNCTIONS

def pick_files_mobile(file_selection_callback: Callable[[List[str]], None]):
    """Show mobile-optimized file picker for selecting PDF files"""
    
    # Start from mobile-friendly directory
    initial_path = get_mobile_documents_path()
    
    file_chooser = FileChooserIconView(
        filters=['*.pdf'],
        multiselect=True,
        size_hint=(1, 0.75),
        path=initial_path
    )
    
    # Mobile-optimized button layout with larger touch targets
    button_layout = BoxLayout(
        size_hint=(1, 0.25), 
        spacing=dp(15), 
        padding=dp(15),
        orientation='horizontal'
    )
    
    cancel_button = Button(
        text="Cancel",
        size_hint=(0.4, 1),
        font_size=sp(16)
    )
    select_button = Button(
        text="Select Files",
        size_hint=(0.6, 1),
        font_size=sp(16)
    )
    
    button_layout.add_widget(cancel_button)
    button_layout.add_widget(select_button)

    # Path indicator for better navigation
    path_label = Label(
        text=f"Location: {file_chooser.path}",
        size_hint=(1, None),
        height=dp(30),
        font_size=sp(12),
        text_size=(None, None)
    )

    content_layout = BoxLayout(orientation='vertical')
    content_layout.add_widget(path_label)
    content_layout.add_widget(file_chooser)
    content_layout.add_widget(button_layout)

    file_picker_popup = Popup(
        title="Select PDF Files", 
        content=content_layout,
        size_hint=(0.95, 0.9),  # Larger for mobile
        auto_dismiss=False
    )

    # Update path label when directory changes
    def update_path_label(instance, path):
        path_label.text = f"Location: {path}"
    
    file_chooser.bind(path=update_path_label)

    cancel_button.bind(on_release=lambda *a: (
        file_picker_popup.dismiss(), 
        file_selection_callback([])
    ))
    
    def handle_file_selection(*args):
        selected = file_chooser.selection
        file_picker_popup.dismiss()
        file_selection_callback(selected)
    
    select_button.bind(on_release=handle_file_selection)
    file_picker_popup.open()


def save_file_dialog_mobile(default_filename: str, save_path_callback: Callable[[Optional[str]], None]):
    """Show mobile-optimized save file dialog"""
    
    initial_path = get_mobile_output_path()
    
    directory_chooser = FileChooserIconView(
        dirselect=True,
        size_hint=(1, 0.6),
        path=initial_path
    )
    
    # Filename input with mobile keyboard considerations
    filename_input = TextInput(
        text=default_filename,
        size_hint=(1, None),
        height=dp(50),
        multiline=False,
        font_size=sp(16),
        hint_text="Enter filename"
    )
    
    # Path display
    path_label = Label(
        text=f"Save to: {directory_chooser.path}",
        size_hint=(1, None),
        height=dp(40),
        font_size=sp(12),
        text_size=(None, None)
    )
    
    # Mobile-optimized buttons
    button_layout = BoxLayout(
        size_hint=(1, 0.2), 
        spacing=dp(15), 
        padding=dp(15)
    )
    cancel_button = Button(
        text="Cancel",
        size_hint=(0.4, 1),
        font_size=sp(16)
    )
    save_button = Button(
        text="Save",
        size_hint=(0.6, 1),
        font_size=sp(16)
    )
    button_layout.add_widget(cancel_button)
    button_layout.add_widget(save_button)

    content_layout = BoxLayout(orientation='vertical')
    content_layout.add_widget(path_label)
    content_layout.add_widget(directory_chooser)
    content_layout.add_widget(filename_input)
    content_layout.add_widget(button_layout)

    save_dialog_popup = Popup(
        title="Save Merged PDF", 
        content=content_layout,
        size_hint=(0.95, 0.9),
        auto_dismiss=False
    )

    # Update path label when directory changes
    def update_path_label(instance, path):
        path_label.text = f"Save to: {path}"
    
    directory_chooser.bind(path=update_path_label)

    cancel_button.bind(on_release=lambda *a: (
        save_dialog_popup.dismiss(), 
        save_path_callback(None)
    ))
    
    def handle_save_action(*args):
        """Validate and process save action"""
        filename = filename_input.text.strip()
        if not filename:
            StatusPopup.show("Error", "Please enter a filename", is_error=True)
            return
            
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
            
        full_path = os.path.join(directory_chooser.path, filename)
        save_dialog_popup.dismiss()
        save_path_callback(full_path)
    
    save_button.bind(on_release=handle_save_action)
    save_dialog_popup.open()

# MOBILE UTILITY FUNCTIONS

def get_mobile_documents_path() -> str:
    """Get mobile-appropriate documents directory"""
    if platform == 'android' and ANDROID_AVAILABLE:
        try:
            # Try to get external storage path
            external_path = primary_external_storage_path()
            if external_path:
                documents_path = os.path.join(external_path, 'Documents')
                if os.path.exists(documents_path):
                    return documents_path
                # Fallback to Downloads
                downloads_path = os.path.join(external_path, 'Download')
                if os.path.exists(downloads_path):
                    return downloads_path
                return external_path
        except:
            pass
    
    # iOS or fallback
    return os.path.expanduser("~/Documents")


def get_mobile_output_path() -> str:
    """Get mobile-appropriate output directory"""
    if platform == 'android' and ANDROID_AVAILABLE:
        try:
            external_path = primary_external_storage_path()
            if external_path:
                downloads_path = os.path.join(external_path, 'Download')
                if os.path.exists(downloads_path):
                    return downloads_path
                return external_path
        except:
            pass
    
    # iOS or fallback
    documents_path = os.path.expanduser("~/Documents")
    return documents_path if os.path.exists(documents_path) else os.path.expanduser("~")


def get_mobile_default_output_path() -> str:
    """Generate default output path on mobile"""
    output_directory = get_mobile_output_path()
    return os.path.join(output_directory, "merged_document.pdf")


def validate_mobile_output_path(output_path: str) -> tuple[bool, str]:
    """Validate if output path is writable on mobile"""
    try:
        output_directory = os.path.dirname(output_path)
        
        # Create directory if it doesn't exist
        if not os.path.exists(output_directory):
            try:
                os.makedirs(output_directory, exist_ok=True)
            except PermissionError:
                return False, "No permission to create directory"
        
        if not os.access(output_directory, os.W_OK):
            return False, "No write permission to directory"
            
        if os.path.exists(output_path) and not os.access(output_path, os.W_OK):
            return False, "Cannot overwrite existing file"
            
        return True, "Path is valid"
    except Exception as error:
        return False, f"Path validation error: {error}"


def format_file_size_mobile(file_path: str) -> str:
    """Format file size in mobile-friendly format"""
    try:
        size_bytes = os.path.getsize(file_path)
        
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.0f}KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f}MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"
    except:
        return "???"


def create_mobile_backup_filename(original_path: str) -> str:
    """Generate mobile-friendly backup filename"""
    if not os.path.exists(original_path):
        return original_path
        
    base_name, file_extension = os.path.splitext(os.path.basename(original_path))
    file_directory = os.path.dirname(original_path)
    timestamp = datetime.now().strftime("%m%d_%H%M")  # Shorter timestamp for mobile
    
    backup_path = os.path.join(file_directory, f"{base_name}_{timestamp}{file_extension}")
    if not os.path.exists(backup_path):
        return backup_path
        
    # Handle filename collisions with simpler numbering
    counter = 1
    while counter < 100:  # Reduced from 1000
        alternative_path = os.path.join(file_directory, f"{base_name}_{counter}{file_extension}")
        if not os.path.exists(alternative_path):
            return alternative_path
        counter += 1
        
    return original_path


def get_available_storage_space() -> str:
    """Get available storage space for mobile devices"""
    try:
        if platform == 'android' and ANDROID_AVAILABLE:
            # Android-specific storage check
            storage_path = get_mobile_output_path()
            statvfs = os.statvfs(storage_path)
            available_bytes = statvfs.f_frsize * statvfs.f_available
            return format_file_size_mobile_bytes(available_bytes)
        else:
            # Generic storage check
            import shutil
            total, used, free = shutil.disk_usage(get_mobile_output_path())
            return format_file_size_mobile_bytes(free)
    except:
        return "Unknown"


def format_file_size_mobile_bytes(size_bytes: int) -> str:
    """Format bytes to mobile-friendly size string"""
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.0f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.0f}MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"