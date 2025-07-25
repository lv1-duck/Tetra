"""This file contains the UI components used in the application.
It includes custom widgets like RoundedBoxLayout, StyledButton, and FileItemWidget."""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from ui.ui_constants import Theme, Sizes
from kivy.uix.label import Label
import os
from core.file_manager_desktop import format_file_size


# CLASSES FOR UI COMPONENTS
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
    def __init__(self, file_path, index, on_remove_callback, on_view_callback, **kwargs):
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
        # FILE INFORMATION
        file_info = BoxLayout(orientation='vertical',
                            spacing=dp(2),
                            padding=[0, dp(5), 0, dp(5)],)
    
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
        # X BUTTON
        remove_button = Button(
            text="X",
            size_hint=(None, 1),
            width=dp(40),
            background_color=(0.8, 0.2, 0.2, 1),
            color=Theme.TEXT_PRIMARY
        )
        remove_button.bind(on_release=lambda x: on_remove_callback(index))
        # VIEW BUTTON
        view_button = Button(
            text="View",
            size_hint=(None, 1),
            width=dp(40),
            background_color=(0.1, 0.1, 0.4),
            color=Theme.TEXT_PRIMARY
        )
        view_button.bind(on_release=lambda x: on_view_callback(file_path))
        
        self.add_widget(file_info)
        self.add_widget(remove_button)
        self.add_widget(view_button)
