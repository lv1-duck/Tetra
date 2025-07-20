from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.behaviors import ButtonBehavior
from kivy.metrics import dp

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

class RoundedButton(ButtonBehavior, Widget):
    def __init__(self, text="", bg_color=(0.5, 0.5, 0.5, 1), text_color=(1, 1, 1, 1), radius=12, font_size=18, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.bg_color = bg_color
        self.text_color = text_color
        self.radius = dp(radius)
        self.font_size = dp(font_size)
        
        with self.canvas.before:
            Color(*self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
        
        # Add label for text
        self.label = Label(
            text=self.text,
            color=self.text_color,
            pos=self.pos,
            size=self.size,
            font_size=self.font_size,
            bold=True
        )
        self.add_widget(self.label)
        
        self.bind(pos=self.update_graphics, size=self.update_graphics)
        
    def update_graphics(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.label.pos = self.pos
        self.label.size = self.size

class RoundedLabel(Widget):
    def __init__(self, text="", bg_color=(0.3, 0.3, 0.3, 1), text_color=(1, 1, 1, 1), radius=10, font_size=16, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.bg_color = bg_color
        self.text_color = text_color
        self.radius = dp(radius)
        self.font_size = dp(font_size)
        
        with self.canvas.before:
            Color(*self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
        
        # Add label for text
        self.label = Label(
            text=self.text,
            color=self.text_color,
            pos=self.pos,
            size=self.size,
            font_size=self.font_size,
            text_size=(None, None),
            halign='left',
            valign='middle'
        )
        self.add_widget(self.label)
        
        self.bind(pos=self.update_graphics, size=self.update_graphics)
        
    def update_graphics(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.label.pos = (self.pos[0] + dp(15), self.pos[1])
        self.label.size = (self.size[0] - dp(30), self.size[1])
        self.label.text_size = (self.size[0] - dp(30), None)

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_files = []
        
        # Master layout with mobile-optimized padding
        self.master = RoundedBoxLayout(
            orientation='vertical', 
            padding=dp(15), 
            spacing=dp(15), 
            bg_color=(30/255, 31/255, 40/255, 1),
            radius=25
        )
        
        # Header section - mobile optimized height
        header = RoundedBoxLayout(
            size_hint_y=None, 
            height=dp(50), 
            bg_color=(46/255, 47/255, 62/255, 1),
            radius=18
        )
        title = Label(
            text="Tetra PDF Utility Tool", 
            color=(1, 1, 1, 1), 
            font_size=dp(24),
            bold=True
        )
        header.add_widget(title)
        self.master.add_widget(header)
        
        # Button section - horizontal layout for space efficiency
        button_container = BoxLayout(
            orientation='horizontal', 
            size_hint_y=None, 
            height=dp(70),  # Height for single row of buttons
            spacing=dp(12)
        )
        
        self.add_files_button = RoundedButton(
            text="Add",
            bg_color=(45/255, 95/255, 145/255, 1),
            text_color=(1, 1, 1, 1),
            radius=15,
            font_size=16,
            size_hint_y=None,
            height=dp(60)
        )
        self.add_files_button.bind(on_release=self.on_select_files)
        
        self.append_button = RoundedButton(
            text="Merge",
            bg_color=(45/255, 115/255, 110/255, 1),
            text_color=(1, 1, 1, 1),
            radius=15,
            font_size=16,
            size_hint_y=None,
            height=dp(60)
        )
        self.append_button.bind(on_release=self.on_merge)
        
        self.viewer_button = RoundedButton(
            text="View",
            bg_color=(65/255, 70/255, 125/255, 1),
            text_color=(1, 1, 1, 1),
            radius=15,
            font_size=16,
            size_hint_y=None,
            height=dp(60)
        )
        self.viewer_button.bind(on_release=self.on_view_pdf)
        
        button_container.add_widget(self.add_files_button)
        button_container.add_widget(self.append_button)
        button_container.add_widget(self.viewer_button)
        self.master.add_widget(button_container)
        
        # Files section header
        files_header = RoundedBoxLayout(
            size_hint_y=None,
            height=dp(50),
            bg_color=(52/255, 54/255, 73/255, 1),
            radius=12
        )
        files_title = Label(
            text="Selected Files",
            color=(1, 1, 1, 1),
            font_size=dp(18),
            bold=True
        )
        files_header.add_widget(files_title)
        self.master.add_widget(files_header)
        
        # File list container - takes remaining space
        file_list_container = RoundedBoxLayout(
            orientation='vertical', 
            spacing=dp(5), 
            bg_color=(41/255, 43/255, 62/255, 1),
            radius=18
        )
        
        self.scrollview = ScrollView(
            bar_width=dp(8),
            bar_color=(1, 1, 1, 0.3),
            bar_inactive_color=(1, 1, 1, 0.1)
        )
        
        self.file_list_layout = BoxLayout(
            orientation='vertical', 
            size_hint_y=None, 
            spacing=dp(8),
            padding=[dp(25), dp(35), dp(25), dp(25)]  # Added top padding for spacing
        )
        self.file_list_layout.bind(minimum_height=self.file_list_layout.setter('height'))
        
        # Add placeholder text when no files
        self.empty_label = Label(
            text="No files selected\nTap 'Add' to get started",
            color=(0.7, 0.7, 0.7, 1),
            font_size=dp(24),
            halign='center',
            text_size=(None, None)
        )
        self.file_list_layout.add_widget(self.empty_label)
        
        self.scrollview.add_widget(self.file_list_layout)
        file_list_container.add_widget(self.scrollview)
        self.master.add_widget(file_list_container)
        
        self.add_widget(self.master)

    def on_select_files(self, instance):
        # Remove empty label if it exists
        if self.empty_label in self.file_list_layout.children:
            self.file_list_layout.remove_widget(self.empty_label)
            
        dummy_files = [f"Document_{i}.pdf" for i in range(len(self.selected_files) + 1, len(self.selected_files) + 3)]
        self.selected_files.extend(dummy_files)
        self.update_file_list()

    def update_file_list(self):
        # Clear existing file widgets (but keep empty label if no files)
        for widget in self.file_list_layout.children[:]:
            if isinstance(widget, RoundedLabel):
                self.file_list_layout.remove_widget(widget)
        
        for i, file in enumerate(self.selected_files):
            file_label = RoundedLabel(
                text=f"{i+1}. {file}",
                size_hint_y=None,
                height=dp(55),
                bg_color=(52/255, 54/255, 73/255, 1),
                text_color=(1, 1, 1, 1),
                radius=12,
                font_size=16
            )
            self.file_list_layout.add_widget(file_label)

    def on_merge(self, instance):
        if len(self.selected_files) < 2:
            print("Need at least 2 files to merge")
        else:
            print(f"Merging {len(self.selected_files)} PDFs...")

    def on_view_pdf(self, instance):
        if not self.selected_files:
            print("No files to view")
        else:
            print(f"Opening PDF viewer for: {self.selected_files[0]}")

class PDFApp(App):
    def build(self):
        self.title = "Tetra PDF Manager"
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        return sm

if __name__ == "__main__":
    PDFApp().run()