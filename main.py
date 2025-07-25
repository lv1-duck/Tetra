from kivy.app import App
import os
from kivy.utils import platform
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.metrics import dp
from kivy.clock import Clock

from ui.status_popup import StatusPopup
from ui.ui_constants import Theme, Sizes
from ui.ui_components import RoundedBoxLayout, StyledButton, FileItemWidget
    
# DESKTOP FILE MANAGER MODULE
from core.file_manager_desktop import (
    DesktopPDFFileManager, 
    FileOperationResult,
    pick_files_desktop, 
    save_file_dialog_desktop,
    validate_desktop_output_path,
    create_backup_filename
)




# MAINSCREEN
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # INIT. FILE MANAGER
        self.file_manager = DesktopPDFFileManager()
        self.file_manager.add_observer(self.on_file_list_changed)
        
        self.setup_ui()

    def setup_ui(self):
        # BACKGROUND
        with self.canvas.before:
            Color(*Theme.BACKGROUND)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(0)])
        self.bind(pos=lambda *a: setattr(self._bg, 'pos', self.pos),
                  size=lambda *a: setattr(self._bg, 'size', self.size))

        # MASTER LAYOUT
        self.master = RoundedBoxLayout(
            orientation='vertical',
            padding=Sizes.PADDING,
            spacing=Sizes.SPACING,
            bg_color=Theme.BACKGROUND,
            radius=Sizes.RADIUS_LARGE
        )
        # HEADER
        header = RoundedBoxLayout(
            size_hint_y=None,
            height=Sizes.HEADER_HEIGHT,
            bg_color=Theme.HEADER_BG,
            radius=Sizes.RADIUS_MEDIUM
        )
        header.add_widget(Label(
            text="PDF Utility Tool - Desktop",
            color=Theme.TEXT_PRIMARY,
            font_size=dp(24),
            bold=True
        ))
        self.master.add_widget(header)
        # BUTTON ROW
        button_container = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=dp(70),
            spacing=Sizes.SPACING
        )
        self.add_button = StyledButton(text="Add Files", on_release=self.open_file_chooser)
        self.merge_button = StyledButton(text="Merge PDFs", on_release=self.show_merge_dialog)
        self.clear_button = StyledButton(text="Clear All", on_release=self.clear_files)
        for button in (self.add_button, self.merge_button, self.clear_button):
            button_container.add_widget(button)
        self.master.add_widget(button_container)
        #FILE LIST CONTAINER HEADER
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
            font_size=dp(18),
            bold=True,
            halign='left',
            valign='middle'
        )
        self.files_count_label.bind(size=self.files_count_label.setter('text_size'))
        header_layout.add_widget(self.files_count_label)
        files_header.add_widget(header_layout)
        self.master.add_widget(files_header)
        # FILE LIST CONTAINER
        list_container = RoundedBoxLayout(
            orientation='vertical',
            spacing=dp(5),
            bg_color=Theme.LIST_BG,
            radius=Sizes.RADIUS_MEDIUM,
            padding=[dp(10), dp(10)]
        )
        self.scrollview = ScrollView(
            bar_width=dp(8),
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
        """Open desktop file chooser"""
        pick_files_desktop(self.on_files_selected)

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
                font_size=dp(16),
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
                on_view_callback=self.view_file  
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
            height=dp(30),
            color=Theme.TEXT_PRIMARY
        ))
        # Filename input with default name
        default_name = f"merged_document_{self.file_manager.get_file_count()}_files.pdf"
        filename_input = TextInput(
            text=default_name,
            size_hint_y=None,
            height=dp(40),
            multiline=False,
            background_color=Theme.ITEM_BG,
            foreground_color=Theme.TEXT_PRIMARY
        )
        content.add_widget(filename_input)
        # Info label
        info_label = Label(
            text="You'll choose the save location in the next step",
            size_hint_y=None,
            height=dp(30),
            color=Theme.TEXT_SECONDARY,
            font_size=dp(12)
        )
        content.add_widget(info_label)
        # Button layout
        button_layout = BoxLayout(
            size_hint_y=None, 
            height=dp(50), 
            spacing=dp(10)
        )
        cancel_btn = Button(
            text="Cancel", 
            background_color=Theme.ERROR,
            color=Theme.TEXT_PRIMARY
        )
        merge_btn = Button(
            text="Choose Location & Merge", 
            background_color=Theme.SUCCESS,
            color=Theme.TEXT_PRIMARY
        )
        button_layout.add_widget(cancel_btn)
        button_layout.add_widget(merge_btn)
        content.add_widget(button_layout)
        popup = Popup(
            title="Merge PDFs",
            content=content,
            size_hint=(0.9, 0.6),
            background_color=Theme.BACKGROUND
        )
        cancel_btn.bind(on_release=popup.dismiss)
        merge_btn.bind(on_release=lambda x: self.choose_save_location_and_merge(filename_input.text.strip(), popup))
        popup.open()

    def choose_save_location_and_merge(self, filename, popup):
        popup.dismiss()
        # VALIDATE FILENAME
        if not filename:
            StatusPopup.show("Error", "Please enter a filename", is_error=True)
            return
        # VALIDATE FILE EXTENSION
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        self.show_loading_popup("Opening save dialog...")
        Clock.schedule_once(lambda dt: self.perform_save_dialog(filename), 0.1)

    def perform_save_dialog(self, filename):
        try:
            def save_callback(output_path):
                self.dismiss_loading_popup()
                if output_path:
                    # VALIDATE THE PATH
                    is_valid, message = validate_desktop_output_path(output_path)
                    if not is_valid:
                        StatusPopup.show("Error", f"Invalid save location: {message}", is_error=True)
                        return
                    
                    # CHECK IF FILE EXISTS, CREATE BACKUP IF NEEDED
                    if os.path.exists(output_path):
                        backup_path = create_backup_filename(output_path)
                        if backup_path != output_path:
                            StatusPopup.show("Info", f"File exists, saving as {os.path.basename(backup_path)}")
                            output_path = backup_path
                    
                    # USER SELECTED A LOCATION, PROCEED WITH MERGE
                    self.perform_merge_with_path(output_path)
                else:
                    # USER CANCELLED THE SAVE DIALOG
                    StatusPopup.show("Info", "Save cancelled by user")
            
            # Call the function with both required arguments
            save_file_dialog_desktop(filename, save_callback)
            
        except Exception as e:
            self.dismiss_loading_popup()
            StatusPopup.show("Error", f"Error showing save dialog: {str(e)}", is_error=True)
            
    def perform_merge_with_path(self, output_path):
        # SHOW PROGRESS POPUP
        self.show_loading_popup(f"Merging {self.file_manager.get_file_count()} PDFs...")
        # PERFORM MERGE IN A SEPERATE THREAD
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
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
        #SUCESS MESSAGE
        success_label = Label(
            text=message,
            color=Theme.SUCCESS,
            text_size=(dp(300), None),
            halign='center'
        )
        content.add_widget(success_label)
        #FILE PATH INFO
        path_label = Label(
            text=f"Saved to:\n{output_path}",
            color=Theme.TEXT_SECONDARY,
            text_size=(dp(300), None),
            halign='center',
            font_size=dp(12)
        )
        content.add_widget(path_label)
        #BUTTON LAYOUT
        button_layout = BoxLayout(
            size_hint_y=None, 
            height=dp(50), 
            spacing=dp(10)
        )
        ok_btn = Button(
            text="OK", 
            background_color=Theme.SUCCESS,
            color=Theme.TEXT_PRIMARY
        )
        try:
            if platform == "win32":
                open_folder_btn = Button(
                    text="Open Folder", 
                    background_color=Theme.BUTTON_BG,
                    color=Theme.TEXT_PRIMARY
                )
                button_layout.add_widget(open_folder_btn)
            elif platform == "darwin":
                open_folder_btn = Button(
                    text="Show in Finder", 
                    background_color=Theme.BUTTON_BG,
                    color=Theme.TEXT_PRIMARY
                )
                button_layout.add_widget(open_folder_btn)
            else:  # Linux
                open_folder_btn = Button(
                    text="Open Folder", 
                    background_color=Theme.BUTTON_BG,
                    color=Theme.TEXT_PRIMARY
                )
                button_layout.add_widget(open_folder_btn)
        except:
            open_folder_btn = None
        button_layout.add_widget(ok_btn)
        content.add_widget(button_layout)
        popup = Popup(
            title="Merge Successful!",
            content=content,
            size_hint=(0.8, 0.6),
            background_color=Theme.BACKGROUND
        )
        ok_btn.bind(on_release=popup.dismiss)
        if 'open_folder_btn' in locals() and open_folder_btn:
            open_folder_btn.bind(on_release=lambda x: self.open_file_location(output_path))
        popup.open()

    def open_file_location(self, file_path):
        """Open file location in system file manager"""
        try:
            import subprocess
            import sys
            if sys.platform == "win32":
                subprocess.run(f'explorer /select,"{file_path}"', shell=True)
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", file_path])
            else:  # Linux
                subprocess.run(["xdg-open", os.path.dirname(file_path)])
        except Exception as e:
            StatusPopup.show("Error", f"Could not open file location: {str(e)}", is_error=True)
            
    # HELPER METHODS FOR LOADING POPUPS
    def show_loading_popup(self, message="Please wait..."):
        if hasattr(self, '_loading_popup') and self._loading_popup:
            return  # Already showing
        content = BoxLayout(
            orientation='vertical', 
            spacing=dp(15), 
            padding=dp(30)
        )
        loading_label = Label(
            text=message,
            color=Theme.TEXT_PRIMARY,
            font_size=dp(16),
            text_size=(dp(250), None),
            halign='center'
        )
        content.add_widget(loading_label)
        # SIMPLE LOADING INDICATOR
        spinner_label = Label(
            text=".", 
            color=Theme.BUTTON_BG,
            font_size=dp(30)
        )
        content.add_widget(spinner_label)
        
        self._loading_popup = Popup(
            title="Processing...",
            content=content,
            size_hint=(0.7, 0.4),
            auto_dismiss=False,  # Dont allow dismissing
            background_color=Theme.BACKGROUND
        )
        self._loading_popup.open()
        self._start_spinner_animation(spinner_label)

    def dismiss_loading_popup(self):
        if hasattr(self, '_loading_popup') and self._loading_popup:
            self._loading_popup.dismiss()
            self._loading_popup = None
            # STOP ANIMATION
            if hasattr(self, '_spinner_event') and self._spinner_event:
                self._spinner_event.cancel()
                self._spinner_event = None

    def _start_spinner_animation(self, spinner_label):
        spinner_chars = [".", "..", "...", "...."] #I WILL SOMEDAY MAKE A REAL AND BETTER SPINNER ANIMATION
        self._spinner_index = 0
        
        def update_spinner(dt):
            if hasattr(self, '_loading_popup') and self._loading_popup:
                self._spinner_index = (self._spinner_index + 1) % len(spinner_chars)
                spinner_label.text = spinner_chars[self._spinner_index]
                return True
            else:
                return False
        self._spinner_event = Clock.schedule_interval(update_spinner, 0.3)
    

#MAIN ENTRY POINT
class PDFApp(App):
    def build(self):
        self.title = "PDF Utility Tool - Desktop"
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        
        #VIEWER SCREEN
        from ui.viewer_screen import ViewerScreen  # Import your ViewerScreen
        viewer_screen = Screen(name='viewer')
        self.viewer_widget = ViewerScreen()
        viewer_screen.add_widget(self.viewer_widget)
        sm.add_widget(viewer_screen)
        
        return sm

if __name__ == "__main__":
    PDFApp().run()