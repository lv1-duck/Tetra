from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.metrics import dp
from ui.ui_constants import Theme

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
        # AUTODISMISS IN 3 SECONDS
        Clock.schedule_once(lambda dt: popup.dismiss(), 5)
 
