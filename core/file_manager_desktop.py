"""
Desktop File Management Module for PDF operations
Handles file selection, validation, and PDF operations for desktop platforms (Windows, macOS, Linux)
Using Kivy popups for file dialogs instead of tkinter.
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
from kivy.uix.filechooser import FileChooserListView
from kivy.metrics import dp

# FILE OPERATION RESULTS CLASS
class FileOperationResult(Enum):
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"

@dataclass
class FileOperationResponse:
    result: FileOperationResult
    message: str
    data: Optional[Any] = None

class DesktopPDFFileManager:
    """Manages PDF file operations and maintains file list state for desktop platforms"""
    def __init__(self):
        self.selected_files: List[str] = []
        self._file_list_observers: List[Callable] = []

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
            return FileOperationResponse(FileOperationResult.ERROR, "No files provided")

        added_files = []
        invalid_files = []
        
        for path in file_paths:
            file_name = os.path.basename(path)
            
            if not os.path.exists(path):
                invalid_files.append(f"{file_name} (not found)")
            elif not path.lower().endswith('.pdf'):
                invalid_files.append(f"{file_name} (not a PDF)")
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
                f"Added {len(added_files)} files; skipped {len(invalid_files)} invalid: {', '.join(invalid_files)}"
            )
        return FileOperationResponse(
            FileOperationResult.ERROR, 
            f"No valid files added: {', '.join(invalid_files)}"
        )

    def remove_file(self, index: int) -> FileOperationResponse:
        """Remove file from selected files list by index"""
        if not (0 <= index < len(self.selected_files)):
            return FileOperationResponse(FileOperationResult.ERROR, "Invalid index")
        
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
            return FileOperationResponse(FileOperationResult.ERROR, "Invalid indices")
        
        file_to_move = self.selected_files.pop(from_index)
        self.selected_files.insert(to_index, file_to_move)
        self._notify_file_list_observers()
        
        return FileOperationResponse(FileOperationResult.SUCCESS, "Reordered files")

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
                "PyMuPDF not installed. Run: pip install PyMuPDF"
            )
        if len(self.selected_files) < 2:
            return FileOperationResponse(
                FileOperationResult.ERROR, 
                "Need at least 2 PDFs to merge"
            )
        
        try:
            # Create a new PDF document
            pdf_merger = fitz.open()
            
            for file_path in self.selected_files:
                if not os.path.exists(file_path):
                    pdf_merger.close()
                    return FileOperationResponse(
                        FileOperationResult.ERROR, 
                        f"Missing: {os.path.basename(file_path)}"
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
                f"Merged {len(self.selected_files)} PDFs to {os.path.basename(output_path)}"
            )
        except Exception as error:
            return FileOperationResponse(
                FileOperationResult.ERROR, 
                f"Merge failed: {error}"
            )

    def _is_valid_pdf(self, path: str) -> bool:
        """Check if file is a valid PDF"""
        if PDF_LIBRARY_AVAILABLE:
            try:
                doc = fitz.open(path)
                is_pdf = doc.is_pdf  # Correct attribute name
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
# FILE PICKER FUNCTIONS

def pick_files_desktop(file_selection_callback: Callable[[List[str]], None]):
    """Show file picker for selecting PDF files"""
    file_chooser = FileChooserListView(
        filters=['*.pdf'],
        multiselect=True,
        size_hint=(1, 0.8)
    )
    
    button_layout = BoxLayout(size_hint=(1, 0.2), spacing=dp(10), padding=dp(10))
    cancel_button = Button(text="Cancel")
    select_button = Button(text="Select")
    button_layout.add_widget(cancel_button)
    button_layout.add_widget(select_button)

    content_layout = BoxLayout(orientation='vertical')
    content_layout.add_widget(file_chooser)
    content_layout.add_widget(button_layout)

    file_picker_popup = Popup(
        title="Select PDF Files", 
        content=content_layout,
        size_hint=(0.9, 0.9), 
        auto_dismiss=False
    )

    cancel_button.bind(on_release=lambda *a: (file_picker_popup.dismiss(), file_selection_callback([])))
    select_button.bind(on_release=lambda *a: (
        file_picker_popup.dismiss(), 
        file_selection_callback(file_chooser.selection)
    ))
    file_picker_popup.open()


def choose_directory_desktop(directory_selection_callback: Callable[[Optional[str]], None]):
    """Show directory picker for selecting output location"""
    directory_chooser = FileChooserListView(
        dirselect=True,
        size_hint=(1, 0.8)
    )
    
    button_layout = BoxLayout(size_hint=(1, 0.2), spacing=dp(10), padding=dp(10))
    cancel_button = Button(text="Cancel")
    select_button = Button(text="Select")
    button_layout.add_widget(cancel_button)
    button_layout.add_widget(select_button)

    content_layout = BoxLayout(orientation='vertical')
    content_layout.add_widget(directory_chooser)
    content_layout.add_widget(button_layout)

    directory_picker_popup = Popup(
        title="Select Directory", 
        content=content_layout,
        size_hint=(0.9, 0.9), 
        auto_dismiss=False
    )

    cancel_button.bind(on_release=lambda *a: (directory_picker_popup.dismiss(), directory_selection_callback(None)))
    select_button.bind(on_release=lambda *a: (
        directory_picker_popup.dismiss(), 
        directory_selection_callback(directory_chooser.path)
    ))
    directory_picker_popup.open()


def save_file_dialog_desktop(default_filename: str, save_path_callback: Callable[[Optional[str]], None]):
    """Show save file dialog for choosing output path"""
    directory_chooser = FileChooserListView(
        dirselect=True,
        size_hint=(1, 0.7)
    )
    
    filename_input = TextInput(
        text=default_filename,
        size_hint=(1, None),
        height=dp(40),
        multiline=False
    )
    
    button_layout = BoxLayout(size_hint=(1, 0.2), spacing=dp(10), padding=dp(10))
    cancel_button = Button(text="Cancel")
    save_button = Button(text="Save")
    button_layout.add_widget(cancel_button)
    button_layout.add_widget(save_button)

    content_layout = BoxLayout(orientation='vertical')
    content_layout.add_widget(directory_chooser)
    content_layout.add_widget(filename_input)
    content_layout.add_widget(button_layout)

    save_dialog_popup = Popup(
        title="Save Merged PDF As...", 
        content=content_layout,
        size_hint=(0.9, 0.9), 
        auto_dismiss=False
    )

    cancel_button.bind(on_release=lambda *a: (save_dialog_popup.dismiss(), save_path_callback(None)))
    
    def handle_save_action(*args):
        """Validate and process save action"""
        filename = filename_input.text.strip()
        if not filename:
            StatusPopup.show("Error", "Enter a filename", is_error=True)
            return
            
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
            
        full_path = os.path.join(directory_chooser.path, filename)
        save_dialog_popup.dismiss()
        save_path_callback(full_path)
    
    save_button.bind(on_release=handle_save_action)
    save_dialog_popup.open()

# OTHER UTILITY FUNCTIONS

def get_desktop_default_output_path() -> str:
    """Generate default output path on desktop"""
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    output_directory = desktop_path if os.path.exists(desktop_path) else os.path.expanduser("~")
    return os.path.join(output_directory, "merged_document.pdf")


def validate_desktop_output_path(output_path: str) -> tuple[bool, str]:
    """Validate if output path is writable"""
    try:
        output_directory = os.path.dirname(output_path)
        os.makedirs(output_directory, exist_ok=True)
        
        if not os.access(output_directory, os.W_OK):
            return False, f"No write permission: {output_directory}"
            
        if os.path.exists(output_path) and not os.access(output_path, os.W_OK):
            return False, f"File not writable: {output_path}"
            
        return True, "Path is valid"
    except Exception as error:
        return False, f"Validation error: {error}"


def format_file_size(file_path: str) -> str:
    """Format file size in human-readable units"""
    try:
        size_bytes = os.path.getsize(file_path)
        size_units = ['B','KB','MB','GB']
        
        for unit in size_units:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
            
        return f"{size_bytes:.1f} TB"
    except:
        return "Unknown size"


def create_backup_filename(original_path: str) -> str:
    """Generate backup filename with timestamp"""
    if not os.path.exists(original_path):
        return original_path
        
    base_name, file_extension = os.path.splitext(os.path.basename(original_path))
    file_directory = os.path.dirname(original_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    backup_path = os.path.join(file_directory, f"{base_name}_{timestamp}{file_extension}")
    if not os.path.exists(backup_path):
        return backup_path
        
    # Handle filename collisions
    counter = 1
    while counter < 1000:
        alternative_path = os.path.join(file_directory, f"{base_name}_{counter:03d}{file_extension}")
        if not os.path.exists(alternative_path):
            return alternative_path
        counter += 1
        
    return original_path