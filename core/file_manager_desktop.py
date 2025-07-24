"""
Desktop File Management Module for PDF operations
Handles file selection, validation, and PDF operations for desktop platforms (Windows, macOS, Linux)
Now uses Kivy popups for file dialogs instead of tkinter.
"""

import os
from typing import List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from ui.status_popup import StatusPopup

try:
    import PyPDF2
    PDF_LIBRARY_AVAILABLE = True
except ImportError:
    PDF_LIBRARY_AVAILABLE = False

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserListView
from kivy.metrics import dp
from kivy.clock import Clock

# Result types for file operations
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
        self._observers: List[Callable] = []

    def add_observer(self, callback: Callable):
        self._observers.append(callback)

    def remove_observer(self, callback: Callable):
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self):
        for callback in self._observers:
            try:
                callback(self.selected_files.copy())
            except Exception as e:
                print(f"Observer notification error: {e}")

    def add_files(self, file_paths: List[str]) -> FileOperationResponse:
        if not file_paths:
            return FileOperationResponse(FileOperationResult.ERROR, "No files provided")

        added, invalid = [], []
        for path in file_paths:
            if not os.path.exists(path):
                invalid.append(f"{os.path.basename(path)} (not found)")
            elif not path.lower().endswith('.pdf'):
                invalid.append(f"{os.path.basename(path)} (not a PDF)")
            elif not self._is_valid_pdf(path):
                invalid.append(f"{os.path.basename(path)} (corrupted)")
            elif path not in self.selected_files:
                self.selected_files.append(path)
                added.append(os.path.basename(path))

        self._notify_observers()
        if added and not invalid:
            return FileOperationResponse(FileOperationResult.SUCCESS, f"Added {len(added)} files")
        if added and invalid:
            return FileOperationResponse(FileOperationResult.SUCCESS, 
                                         f"Added {len(added)} files; skipped {len(invalid)} invalid: {', '.join(invalid)}")
        return FileOperationResponse(FileOperationResult.ERROR, f"No valid files added: {', '.join(invalid)}")

    def remove_file(self, index: int) -> FileOperationResponse:
        if not (0 <= index < len(self.selected_files)):
            return FileOperationResponse(FileOperationResult.ERROR, "Invalid index")
        removed = os.path.basename(self.selected_files.pop(index))
        self._notify_observers()
        return FileOperationResponse(FileOperationResult.SUCCESS, f"Removed {removed}")

    def clear_files(self) -> FileOperationResponse:
        count = len(self.selected_files)
        self.selected_files.clear()
        self._notify_observers()
        return FileOperationResponse(FileOperationResult.SUCCESS, f"Cleared {count} files")

    def move_file(self, from_idx: int, to_idx: int) -> FileOperationResponse:
        if not (0 <= from_idx < len(self.selected_files) and 0 <= to_idx < len(self.selected_files)):
            return FileOperationResponse(FileOperationResult.ERROR, "Invalid indices")
        file = self.selected_files.pop(from_idx)
        self.selected_files.insert(to_idx, file)
        self._notify_observers()
        return FileOperationResponse(FileOperationResult.SUCCESS, "Reordered files")

    def get_files(self) -> List[str]:
        return self.selected_files.copy()

    def get_file_count(self) -> int:
        return len(self.selected_files)

    def merge_pdfs(self, output_path: str) -> FileOperationResponse:
        if not PDF_LIBRARY_AVAILABLE:
            return FileOperationResponse(FileOperationResult.ERROR, 
                                         "PyPDF2 not installed. Run: pip install PyPDF2")
        if len(self.selected_files) < 2:
            return FileOperationResponse(FileOperationResult.ERROR, "Need at least 2 PDFs to merge")
        try:
            merger = PyPDF2.PdfMerger()
            for f in self.selected_files:
                if not os.path.exists(f):
                    return FileOperationResponse(FileOperationResult.ERROR, f"Missing: {os.path.basename(f)}")
                merger.append(f)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as out_f:
                merger.write(out_f)
            merger.close()
            return FileOperationResponse(FileOperationResult.SUCCESS, 
                                         f"Merged {len(self.selected_files)} PDFs to {os.path.basename(output_path)}")
        except Exception as e:
            return FileOperationResponse(FileOperationResult.ERROR, f"Merge failed: {e}")

    def _is_valid_pdf(self, path: str) -> bool:
        if PDF_LIBRARY_AVAILABLE:
            try:
                with open(path, 'rb') as f:
                    PyPDF2.PdfReader(f)
                return True
            except:
                return False
        else:
            try:
                with open(path, 'rb') as f:
                    return f.read(4) == b'%PDF'
            except:
                return False

# --- Kivy-based file dialogs ---

def pick_files_desktop(callback: Callable[[List[str]], None]):
    """Show a Kivy popup to pick multiple PDF files."""
    chooser = FileChooserListView(
        filters=['*.pdf'],
        multiselect=True,
        size_hint=(1, 0.8)
    )
    btn_layout = BoxLayout(size_hint=(1, 0.2), spacing=dp(10), padding=dp(10))
    cancel = Button(text="Cancel")
    select = Button(text="Select")
    btn_layout.add_widget(cancel)
    btn_layout.add_widget(select)

    content = BoxLayout(orientation='vertical')
    content.add_widget(chooser)
    content.add_widget(btn_layout)

    popup = Popup(title="Select PDF Files", content=content,
                  size_hint=(0.9, 0.9), auto_dismiss=False)

    cancel.bind(on_release=lambda *a: (popup.dismiss(), callback([])))
    select.bind(on_release=lambda *a: (popup.dismiss(), callback(chooser.selection)))
    popup.open()


def choose_directory_desktop(callback: Callable[[Optional[str]], None]):
    """Show a Kivy popup to pick a directory."""
    chooser = FileChooserListView(
        dirselect=True,
        size_hint=(1, 0.8)
    )
    btn_layout = BoxLayout(size_hint=(1, 0.2), spacing=dp(10), padding=dp(10))
    cancel = Button(text="Cancel")
    select = Button(text="Select")
    btn_layout.add_widget(cancel)
    btn_layout.add_widget(select)

    content = BoxLayout(orientation='vertical')
    content.add_widget(chooser)
    content.add_widget(btn_layout)

    popup = Popup(title="Select Directory", content=content,
                  size_hint=(0.9, 0.9), auto_dismiss=False)

    cancel.bind(on_release=lambda *a: (popup.dismiss(), callback(None)))
    select.bind(on_release=lambda *a: (popup.dismiss(), callback(chooser.path)))
    popup.open()


def save_file_dialog_desktop(default_filename: str, callback: Callable[[Optional[str]], None]):
    """Show a Kivy popup to choose save location and filename."""
    chooser = FileChooserListView(
        dirselect=True,
        size_hint=(1, 0.7)
    )
    filename_input = TextInput(
        text=default_filename,
        size_hint=(1, None),
        height=dp(40),
        multiline=False
    )
    btn_layout = BoxLayout(size_hint=(1, 0.2), spacing=dp(10), padding=dp(10))
    cancel = Button(text="Cancel")
    save = Button(text="Save")
    btn_layout.add_widget(cancel)
    btn_layout.add_widget(save)

    content = BoxLayout(orientation='vertical')
    content.add_widget(chooser)
    content.add_widget(filename_input)
    content.add_widget(btn_layout)

    popup = Popup(title="Save Merged PDF As...", content=content,
                  size_hint=(0.9, 0.9), auto_dismiss=False)

    cancel.bind(on_release=lambda *a: (popup.dismiss(), callback(None)))
    def _do_save(*args):
        fname = filename_input.text.strip()
        if not fname:
            StatusPopup.show("Error", "Enter a filename", is_error=True)
            return
        if not fname.lower().endswith('.pdf'):
            fname += '.pdf'
        path = os.path.join(chooser.path, fname)
        popup.dismiss()
        callback(path)
    save.bind(on_release=_do_save)

    popup.open()

# Other utility functions

def get_desktop_default_output_path() -> str:
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    return os.path.join(desktop if os.path.exists(desktop) else os.path.expanduser("~"), "merged_document.pdf")


def validate_desktop_output_path(output_path: str) -> tuple[bool, str]:
    try:
        dir_ = os.path.dirname(output_path)
        os.makedirs(dir_, exist_ok=True)
        if not os.access(dir_, os.W_OK):
            return False, f"No write permission: {dir_}"
        if os.path.exists(output_path) and not os.access(output_path, os.W_OK):
            return False, f"File not writable: {output_path}"
        return True, "Path is valid"
    except Exception as e:
        return False, f"Validation error: {e}"


def format_file_size(file_path: str) -> str:
    try:
        size = os.path.getsize(file_path)
        for unit in ['B','KB','MB','GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    except:
        return "Unknown size"


def create_backup_filename(original_path: str) -> str:
    if not os.path.exists(original_path):
        return original_path
    base, ext = os.path.splitext(os.path.basename(original_path))
    dir_ = os.path.dirname(original_path)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(dir_, f"{base}_{ts}{ext}")
    if not os.path.exists(backup):
        return backup
    cnt = 1
    while cnt < 1000:
        alt = os.path.join(dir_, f"{base}_{cnt:03d}{ext}")
        if not os.path.exists(alt):
            return alt
        cnt += 1
    return original_path
