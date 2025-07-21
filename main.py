from kivy.app import App
import os
from kivy.utils import platform
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.metrics import dp
from kivy.clock import Clock

# Import our modularized file manager
from core.file_manager import (
    PDFFileManager, 
    FileOperationResult,
    pick_files_desktop, 
    pick_files_mobile,
    get_default_output_path,
    format_file_size
)

# Constants for theming
class Theme:
    BACKGROUND = (30/255, 31/255, 40/255, 1)
    HEADER_BG = (46/255, 47/255, 62/255, 1)
    BUTTON_BG = (45/255, 95/255, 145/255, 1)
    LIST_BG = (41/255, 43/255, 62/255, 1)
    ITEM_BG = (52/255, 54/255, 73/255, 1)
    TEXT_PRIMARY = (1, 1, 1, 1)
    TEXT_SECONDARY = (0.7, 0.7, 0.7, 1)
    SUCCESS = (0.2, 0.8, 0.2, 1)
    ERROR = (0.8, 0.2, 0.2, 1)

class Sizes:
    PADDING = dp(15)
    SPACING = dp(12)
    HEADER_HEIGHT = dp(50)
    BUTTON_HEIGHT = dp(60)
    LIST_ITEM_HEIGHT = dp(55)
    RADIUS_LARGE = dp(25)
    RADIUS_MEDIUM = dp(18)
    RADIUS_SMALL = dp(12)


class RoundedBoxLayout(BoxLayout):
    def __init__(self, bg_color=(1, 1, 1, 1), radius=15, **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.radius = dp(radius)
        with self.canvas.before:
            Color(*self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


class StyledButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)  # Transparent
        with self.canvas.before:
            Color(*Theme.BUTTON_BG)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[Sizes.RADIUS_MEDIUM])
        self.bind(pos=self.update_graphics, size=self.update_graphics)
        self.color = Theme.TEXT_PRIMARY

    def update_graphics(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


class FileItemWidget(RoundedBoxLayout):
    def __init__(self, file_path, index, on_remove_callback, **kwargs):
        super().__init__(
            orientation='horizontal',
            bg_color=Theme.ITEM_BG,
            radius=Sizes.RADIUS_SMALL,
            size_hint_y=None,
            height=Sizes.LIST_ITEM_HEIGHT,
            padding=[dp(10), 0],
            spacing=dp(10),
            **kwargs
        )
        
        self.file_path = file_path
        self.index = index
        
        # File info
        file_info = BoxLayout(orientation='vertical', spacing=dp(2))
        file_name = Label(
            text=f"{index + 1}. {os.path.basename(file_path)}",
            color=Theme.TEXT_PRIMARY,
            font_size=dp(14),
            halign='left',
            size_hint_y=0.6
        )
        file_name.bind(size=file_name.setter('text_size'))
        
        file_size = Label(
            text=format_file_size(file_path),
            color=Theme.TEXT_SECONDARY,
            font_size=dp(11),
            halign='left',
            size_hint_y=0.4
        )
        file_size.bind(size=file_size.setter('text_size'))
        
        file_info.add_widget(file_name)
        file_info.add_widget(file_size)
        
        # Remove button
        remove_btn = Button(
            text="✕",
            size_hint=(None, 1),
            width=dp(40),
            background_color=(0.8, 0.2, 0.2, 1),
            color=Theme.TEXT_PRIMARY
        )
        remove_btn.bind(on_release=lambda x: on_remove_callback(index))
        
        self.add_widget(file_info)
        self.add_widget(remove_btn)


class StatusPopup:
    @staticmethod
    def show(title, message, is_error=False):
        color = Theme.ERROR if is_error else Theme.SUCCESS
        content = BoxLayout(orientation='vertical', spacing=dp(10))
        
        label = Label(
            text=message,
            color=color,
            text_size=(dp(300), None),
            halign='center'
        )
        content.add_widget(label)
        
        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.8, 0.4),
            auto_dismiss=True
        )
        popup.open()
        
        # Auto dismiss after 3 seconds
        Clock.schedule_once(lambda dt: popup.dismiss(), 3)


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Initialize file manager
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

        # Master layout
        self.master = RoundedBoxLayout(
            orientation='vertical',
            padding=Sizes.PADDING,
            spacing=Sizes.SPACING,
            bg_color=Theme.BACKGROUND,
            radius=Sizes.RADIUS_LARGE
        )
        
        # Header
        header = RoundedBoxLayout(
            size_hint_y=None,
            height=Sizes.HEADER_HEIGHT,
            bg_color=Theme.HEADER_BG,
            radius=Sizes.RADIUS_MEDIUM
        )
        header.add_widget(Label(
            text="Tetra PDF Utility Tool",
            color=Theme.TEXT_PRIMARY,
            font_size=dp(24),
            bold=True
        ))
        self.master.add_widget(header)
        
        # Button row
        button_container = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=dp(70),
            spacing=Sizes.SPACING
        )
        
        self.add_btn = StyledButton(text="Add Files", on_release=self.open_file_chooser)
        self.merge_btn = StyledButton(text="Merge PDFs", on_release=self.show_merge_dialog)
        self.clear_btn = StyledButton(text="Clear All", on_release=self.clear_files)
        
        for btn in (self.add_btn, self.merge_btn, self.clear_btn):
            button_container.add_widget(btn)
        
        self.master.add_widget(button_container)
        
        # Files header
        files_header = RoundedBoxLayout(
            size_hint_y=None,
            height=Sizes.HEADER_HEIGHT,
            bg_color=Theme.LIST_BG,
            radius=Sizes.RADIUS_SMALL
        )
        
        header_layout = BoxLayout(orientation='horizontal', padding=[dp(15), dp(12), dp(15), dp(12)])
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
        
        # File list container
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
        if platform in ('android', 'ios'):
            pick_files_mobile(self.on_files_selected, platform)
        else:
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
                on_remove_callback=self.remove_file
            )
            self.file_list_layout.add_widget(file_item)

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
        if self.file_manager.get_file_count() < 2:
            StatusPopup.show("Error", "Need at least 2 files to merge", is_error=True)
            return
        
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
        
        content.add_widget(Label(
            text="Enter output filename:",
            size_hint_y=None,
            height=dp(30)
        ))
        
        filename_input = TextInput(
            text="merged_document.pdf",
            size_hint_y=None,
            height=dp(40),
            multiline=False
        )
        content.add_widget(filename_input)
        
        button_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        
        cancel_btn = Button(text="Cancel", background_color=Theme.ERROR)
        merge_btn = Button(text="Merge", background_color=Theme.SUCCESS)
        
        button_layout.add_widget(cancel_btn)
        button_layout.add_widget(merge_btn)
        content.add_widget(button_layout)
        
        popup = Popup(
            title="Merge PDFs",
            content=content,
            size_hint=(0.8, 0.5)
        )
        
        cancel_btn.bind(on_release=popup.dismiss)
        merge_btn.bind(on_release=lambda x: self.perform_merge(filename_input.text, popup))
        
        popup.open()

    def perform_merge(self, filename, popup):
        popup.dismiss()
        
        if not filename.strip():
            StatusPopup.show("Error", "Please enter a filename", is_error=True)
            return
        
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        
        output_path = os.path.join(os.path.dirname(get_default_output_path()), filename)
        
        response = self.file_manager.merge_pdfs(output_path)
        
        if response.result == FileOperationResult.SUCCESS:
            StatusPopup.show("Merge Complete", response.message)
        else:
            StatusPopup.show("Merge Failed", response.message, is_error=True)


class PDFApp(App):
    def build(self):
        self.title = "Tetra PDF Manager"
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        return sm


if __name__ == "__main__":
    PDFApp().run()