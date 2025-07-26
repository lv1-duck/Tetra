from kivy.app import App
from kivy.utils import platform
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.clock import Clock
import os

# UI imports
from ui.status_popup import StatusPopup
from ui.ui_constants import Theme, Sizes
from ui.ui_components import RoundedBoxLayout, StyledButton, FileItemWidget

# PLATFORM DETECTION AND CONDITIONAL IMPORTS
if platform in ('android', 'ios'):
    # Mobile imports
    from core.file_manager_mobile import (
        MobilePDFFileManager as PDFFileManager,
        FileOperationResult,
        pick_files_mobile as pick_files,
        save_file_dialog_mobile as save_file_dialog,
        get_mobile_default_output_path as get_default_output_path,
        validate_mobile_output_path as validate_output_path,
        request_storage_permissions
    )
    MOBILE_PLATFORM = True
    CURRENT_PLATFORM = platform
else:
    # Desktop imports
    from core.file_manager_desktop import (
        DesktopPDFFileManager as PDFFileManager,
        FileOperationResult,
        pick_files_desktop as pick_files,
        save_file_dialog_desktop as save_file_dialog,
        get_desktop_default_output_path as get_default_output_path,
        validate_desktop_output_path as validate_output_path,
        create_backup_filename
    )
    MOBILE_PLATFORM = False
    CURRENT_PLATFORM = 'desktop'

# Platform-specific UI constants
if MOBILE_PLATFORM:
    BUTTON_HEIGHT = dp(60)  # Larger touch targets
    FONT_SIZE_LARGE = dp(20)
    FONT_SIZE_MEDIUM = dp(16)
    PADDING_MOBILE = dp(15)
else:
    BUTTON_HEIGHT = dp(50)
    FONT_SIZE_LARGE = dp(18)
    FONT_SIZE_MEDIUM = dp(14)
    PADDING_MOBILE = dp(10)

# MAIN SCREEN WITH PLATFORM ADAPTATIONS
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Initialize file manager with platform-specific settings
        if MOBILE_PLATFORM:
            self.file_manager = PDFFileManager(platform=CURRENT_PLATFORM)
            # Request permissions on Android
            if CURRENT_PLATFORM == 'android':
                request_storage_permissions(CURRENT_PLATFORM)
        else:
            self.file_manager = PDFFileManager()
            
        self.file_manager.add_observer(self.on_file_list_changed)
        self.setup_ui()

    def setup_ui(self):
        # Background
        with self.canvas.before:
            Color(*Theme.BACKGROUND)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(0)])
        self.bind(pos=lambda *a: setattr(self._bg, 'pos', self.pos),
                  size=lambda *a: setattr(self._bg, 'size', self.size))

        # Master layout with platform-specific padding
        padding = PADDING_MOBILE if MOBILE_PLATFORM else Sizes.PADDING
        self.master = RoundedBoxLayout(
            orientation='vertical',
            padding=padding,
            spacing=Sizes.SPACING,
            bg_color=Theme.BACKGROUND,
            radius=Sizes.RADIUS_LARGE
        )
        
        # Header with platform-specific title
        header = RoundedBoxLayout(
            size_hint_y=None,
            height=Sizes.HEADER_HEIGHT,
            bg_color=Theme.HEADER_BG,
            radius=Sizes.RADIUS_MEDIUM
        )
        
        platform_name = "Mobile" if MOBILE_PLATFORM else "Desktop"
        header.add_widget(Label(
            text=f"PDF Utility Tool - {platform_name}",
            color=Theme.TEXT_PRIMARY,
            font_size=FONT_SIZE_LARGE,
            bold=True
        ))
        self.master.add_widget(header)
        
        # Button row with platform-specific sizing
        button_container = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=BUTTON_HEIGHT + dp(10),
            spacing=Sizes.SPACING
        )
        
        self.add_button = StyledButton(
            text="Add Files", 
            on_release=self.open_file_chooser,
            size_hint_y=None,
            height=BUTTON_HEIGHT
        )
        self.merge_button = StyledButton(
            text="Merge PDFs", 
            on_release=self.show_merge_dialog,
            size_hint_y=None,
            height=BUTTON_HEIGHT
        )
        self.clear_button = StyledButton(
            text="Clear All", 
            on_release=self.clear_files,
            size_hint_y=None,
            height=BUTTON_HEIGHT
        )
        
        for button in (self.add_button, self.merge_button, self.clear_button):
            button_container.add_widget(button)
        self.master.add_widget(button_container)
        
        # Files header
        files_header = RoundedBoxLayout(
            size_hint_y=None,
            height=Sizes.HEADER_HEIGHT,
            bg_color=Theme.LIST_BG,
            radius=Sizes.RADIUS_SMALL
        )
        header_layout = BoxLayout(orientation='horizontal',
                                  padding=[dp(15), dp(12), dp(15), dp(12)])
        
        self.files_count_label = Label(
            text="Selected Files (0)",
            color=Theme.TEXT_PRIMARY,
            font_size=FONT_SIZE_MEDIUM,
            bold=True,
            halign='left',
            valign='middle'
        )
        self.files_count_label.bind(size=self.files_count_label.setter('text_size'))
        header_layout.add_widget(self.files_count_label)
        files_header.add_widget(header_layout)
        self.master.add_widget(files_header)
        
        # File list container
        list_container = RoundedBoxLayout(
            orientation='vertical',
            spacing=dp(5),
            bg_color=Theme.LIST_BG,
            radius=Sizes.RADIUS_MEDIUM,
            padding=[dp(10), dp(10)]
        )
        self.scrollview = ScrollView(
            bar_width=dp(12) if MOBILE_PLATFORM else dp(8),  # Wider scrollbar on mobile
            bar_color=(1, 1, 1, 0.3),
            bar_inactive_color=(1, 1, 1, 0.1)
        )
        self.file_list_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(8)
        )
        self.file_list_layout.bind(minimum_height=self.file_list_layout.setter('height'))
        self.scrollview.add_widget(self.file_list_layout)
        list_container.add_widget(self.scrollview)
        self.master.add_widget(list_container)
        self.add_widget(self.master)
        self.update_file_list_display()

    def open_file_chooser(self, instance):
        """Open platform-appropriate file chooser"""
        if MOBILE_PLATFORM:
            pick_files(self.on_files_selected, CURRENT_PLATFORM)
        else:
            pick_files(self.on_files_selected)

    def on_files_selected(self, file_paths):
        if not file_paths:
            return
        response = self.file_manager.add_files(file_paths)
        if response.result == FileOperationResult.SUCCESS:
            StatusPopup.show("Success", response.message)
        else:
            StatusPopup.show("Error", response.message, is_error=True)

    def on_file_list_changed(self, file_list):
        """Called when file manager notifies of changes"""
        self.update_file_list_display()

    def update_file_list_display(self):
        self.file_list_layout.clear_widgets()
        file_count = self.file_manager.get_file_count()
        self.files_count_label.text = f"Selected Files ({file_count})"
        
        if file_count == 0:
            empty_label = Label(
                text="No files selected\nTap 'Add Files' to get started",
                color=Theme.TEXT_SECONDARY,
                halign='center',
                font_size=FONT_SIZE_MEDIUM,
                size_hint_y=None,
                height=dp(100)
            )
            empty_label.bind(size=empty_label.setter('text_size'))
            self.file_list_layout.add_widget(empty_label)
            return
        
        for index, file_path in enumerate(self.file_manager.get_files()):
            file_item = FileItemWidget(
                file_path=file_path,
                index=index,
                on_remove_callback=self.remove_file,
                on_view_callback=self.view_file,
                mobile_mode=MOBILE_PLATFORM  # Pass mobile mode to widget
            )
            self.file_list_layout.add_widget(file_item)

    def view_file(self, file_path):
        try:
            sm = self.manager
            app = App.get_running_app()
            app.viewer_widget.load_pdf(file_path)
            sm.current = 'viewer'
        except Exception as e:
            StatusPopup.show("Error", f"Could not open PDF viewer: {str(e)}", is_error=True)

    def remove_file(self, index):
        response = self.file_manager.remove_file(index)
        StatusPopup.show("File Removed", response.message)

    def clear_files(self, instance):
        if self.file_manager.get_file_count() == 0:
            StatusPopup.show("Info", "No files to clear")
            return        
        response = self.file_manager.clear_files()
        StatusPopup.show("Files Cleared", response.message)

    def show_merge_dialog(self, instance):
        """Show merge dialog with filename input"""
        if self.file_manager.get_file_count() < 2:
            StatusPopup.show("Error", "Need at least 2 files to merge", is_error=True)
            return
            
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
        
        # Title
        content.add_widget(Label(
            text="Enter filename for merged PDF:",
            size_hint_y=None,
            height=dp(40) if MOBILE_PLATFORM else dp(30),
            color=Theme.TEXT_PRIMARY,
            font_size=FONT_SIZE_MEDIUM
        ))
        
        # Filename input with default name
        default_name = f"merged_document_{self.file_manager.get_file_count()}_files.pdf"
        filename_input = TextInput(
            text=default_name,
            size_hint_y=None,
            height=dp(50) if MOBILE_PLATFORM else dp(40),
            multiline=False,
            background_color=Theme.ITEM_BG,
            foreground_color=Theme.TEXT_PRIMARY,
            font_size=FONT_SIZE_MEDIUM
        )
        content.add_widget(filename_input)
        
        # Platform-specific info
        if MOBILE_PLATFORM:
            info_text = f"Will save to {CURRENT_PLATFORM.title()} default location"
        else:
            info_text = "You'll choose the save location in the next step"
            
        info_label = Label(
            text=info_text,
            size_hint_y=None,
            height=dp(40) if MOBILE_PLATFORM else dp(30),
            color=Theme.TEXT_SECONDARY,
            font_size=dp(12)
        )
        content.add_widget(info_label)
        
        # Button layout
        button_layout = BoxLayout(
            size_hint_y=None, 
            height=BUTTON_HEIGHT, 
            spacing=dp(10)
        )
        cancel_btn = Button(
            text="Cancel", 
            background_color=Theme.ERROR,
            color=Theme.TEXT_PRIMARY
        )
        merge_btn = Button(
            text="Merge PDFs", 
            background_color=Theme.SUCCESS,
            color=Theme.TEXT_PRIMARY
        )
        button_layout.add_widget(cancel_btn)
        button_layout.add_widget(merge_btn)
        content.add_widget(button_layout)
        
        popup = Popup(
            title="Merge PDFs",
            content=content,
            size_hint=(0.95, 0.7) if MOBILE_PLATFORM else (0.9, 0.6),
            background_color=Theme.BACKGROUND
        )
        
        cancel_btn.bind(on_release=popup.dismiss)
        merge_btn.bind(on_release=lambda x: self.handle_merge_request(filename_input.text.strip(), popup))
        popup.open()

    def handle_merge_request(self, filename, popup):
        """Handle merge request with platform-specific logic"""
        popup.dismiss()
        
        if not filename:
            StatusPopup.show("Error", "Please enter a filename", is_error=True)
            return
            
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        
        if MOBILE_PLATFORM:
            # Mobile: Use default path
            output_path = get_default_output_path(CURRENT_PLATFORM)
            if output_path:
                # Replace default filename with user's choice
                output_path = os.path.join(os.path.dirname(output_path), filename)
                self.perform_merge_with_path(output_path)
            else:
                StatusPopup.show("Error", "Could not determine save location", is_error=True)
        else:
            # Desktop: Show save dialog
            self.show_loading_popup("Opening save dialog...")
            Clock.schedule_once(lambda dt: self.perform_save_dialog(filename), 0.1)

    def perform_save_dialog(self, filename):
        """Desktop-specific save dialog"""
        try:
            def save_callback(output_path):
                self.dismiss_loading_popup()
                if output_path:
                    is_valid, message = validate_output_path(output_path)
                    if not is_valid:
                        StatusPopup.show("Error", f"Invalid save location: {message}", is_error=True)
                        return
                    
                    if os.path.exists(output_path):
                        backup_path = create_backup_filename(output_path)
                        if backup_path != output_path:
                            StatusPopup.show("Info", f"File exists, saving as {os.path.basename(backup_path)}")
                            output_path = backup_path
                    
                    self.perform_merge_with_path(output_path)
                else:
                    StatusPopup.show("Info", "Save cancelled by user")
            
            save_file_dialog(filename, save_callback)
            
        except Exception as e:
            self.dismiss_loading_popup()
            StatusPopup.show("Error", f"Error showing save dialog: {str(e)}", is_error=True)
            
    def perform_merge_with_path(self, output_path):
        """Perform merge operation"""
        self.show_loading_popup(f"Merging {self.file_manager.get_file_count()} PDFs...")
        Clock.schedule_once(lambda dt: self.do_merge_operation(output_path), 0.1)

    def do_merge_operation(self, output_path):
        try:
            response = self.file_manager.merge_pdfs(output_path)
            self.dismiss_loading_popup()
            if response.result == FileOperationResult.SUCCESS:
                self.show_merge_success_dialog(output_path, response.message)
            else:
                StatusPopup.show("Error", response.message, is_error=True)
        except Exception as e:
            self.dismiss_loading_popup()
            StatusPopup.show("Error", f"Merge operation failed: {str(e)}", is_error=True)

    def show_merge_success_dialog(self, output_path, message):
        """Show success dialog with platform-specific options"""
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
        
        success_label = Label(
            text=message,
            color=Theme.SUCCESS,
            text_size=(dp(300), None),
            halign='center'
        )
        content.add_widget(success_label)
        
        path_label = Label(
            text=f"Saved to:\n{output_path}",
            color=Theme.TEXT_SECONDARY,
            text_size=(dp(300), None),
            halign='center',
            font_size=dp(12)
        )
        content.add_widget(path_label)
        
        button_layout = BoxLayout(
            size_hint_y=None, 
            height=BUTTON_HEIGHT, 
            spacing=dp(10)
        )
        
        ok_btn = Button(
            text="OK", 
            background_color=Theme.SUCCESS,
            color=Theme.TEXT_PRIMARY
        )
        button_layout.add_widget(ok_btn)
        
        # Platform-specific "open folder" button
        if not MOBILE_PLATFORM:
            try:
                if platform == "win32":
                    folder_btn_text = "Open Folder"
                elif platform == "darwin":
                    folder_btn_text = "Show in Finder"
                else:
                    folder_btn_text = "Open Folder"
                    
                open_folder_btn = Button(
                    text=folder_btn_text, 
                    background_color=Theme.BUTTON_BG,
                    color=Theme.TEXT_PRIMARY
                )
                button_layout.add_widget(open_folder_btn)
                
            except:
                open_folder_btn = None
        
        content.add_widget(button_layout)
        
        popup = Popup(
            title="Merge Successful!",
            content=content,
            size_hint=(0.9, 0.7) if MOBILE_PLATFORM else (0.8, 0.6),
            background_color=Theme.BACKGROUND
        )
        
        ok_btn.bind(on_release=popup.dismiss)
        if not MOBILE_PLATFORM and 'open_folder_btn' in locals() and open_folder_btn:
            open_folder_btn.bind(on_release=lambda x: self.open_file_location(output_path))
            
        popup.open()

    def open_file_location(self, file_path):
        """Open file location in system file manager (desktop only)"""
        try:
            import subprocess
            import sys
            if sys.platform == "win32":
                subprocess.run(f'explorer /select,"{file_path}"', shell=True)
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", file_path])
            else:
                subprocess.run(["xdg-open", os.path.dirname(file_path)])
        except Exception as e:
            StatusPopup.show("Error", f"Could not open file location: {str(e)}", is_error=True)
            
    # Loading popup methods
    def show_loading_popup(self, message="Please wait..."):
        if hasattr(self, '_loading_popup') and self._loading_popup:
            return
            
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(30))
        loading_label = Label(
            text=message,
            color=Theme.TEXT_PRIMARY,
            font_size=FONT_SIZE_MEDIUM,
            text_size=(dp(250), None),
            halign='center'
        )
        content.add_widget(loading_label)
        
        spinner_label = Label(
            text=".", 
            color=Theme.BUTTON_BG,
            font_size=dp(30)
        )
        content.add_widget(spinner_label)
        
        self._loading_popup = Popup(
            title="Processing...",
            content=content,
            size_hint=(0.8, 0.5) if MOBILE_PLATFORM else (0.7, 0.4),
            auto_dismiss=False,
            background_color=Theme.BACKGROUND
        )
        self._loading_popup.open()
        self._start_spinner_animation(spinner_label)

    def dismiss_loading_popup(self):
        if hasattr(self, '_loading_popup') and self._loading_popup:
            self._loading_popup.dismiss()
            self._loading_popup = None
            if hasattr(self, '_spinner_event') and self._spinner_event:
                self._spinner_event.cancel()
                self._spinner_event = None

    def _start_spinner_animation(self, spinner_label):
        spinner_chars = [".", "..", "...", "...."] # I WILL SOMEDAY MAKE A REAL AND BETTER SPINNER ANIMATION
        self._spinner_index = 0
        
        def update_spinner(dt):
            if hasattr(self, '_loading_popup') and self._loading_popup:
                self._spinner_index = (self._spinner_index + 1) % len(spinner_chars)
                spinner_label.text = spinner_chars[self._spinner_index]
                return True
            return False
            
        self._spinner_event = Clock.schedule_interval(update_spinner, 0.3)


# MAIN APP CLASS
class PDFApp(App):
    def build(self):
        platform_name = "Mobile" if MOBILE_PLATFORM else "Desktop"
        self.title = f"PDF Utility Tool - {platform_name}"
        
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        
        # Platform-specific viewer
        if MOBILE_PLATFORM:
            try:
                from ui.mobile_viewer_screen import ViewerScreen
                viewer_screen = Screen(name='viewer')
                self.viewer_widget = ViewerScreen()
                viewer_screen.add_widget(self.viewer_widget)
                sm.add_widget(viewer_screen)
            except ImportError:
                print("Mobile viewer not available")
        else:
            try:
                from ui.viewer_screen import ViewerScreen
                viewer_screen = Screen(name='viewer')
                self.viewer_widget = ViewerScreen()
                viewer_screen.add_widget(self.viewer_widget)
                sm.add_widget(viewer_screen)
            except ImportError:
                print("Desktop viewer not available")
        
        return sm


if __name__ == "__main__":
    PDFApp().run()