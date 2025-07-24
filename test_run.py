from kivy.app import App
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserIconView

from ui.viewer_screen import ViewerScreen

class PDFViewerApp(App):
    def build(self):
        self.viewer = ViewerScreen()
        Clock.schedule_once(self.open_filechooser, 0)
        return self.viewer

    def open_filechooser(self, dt):
        chooser = FileChooserIconView(filters=['*.pdf'], size_hint=(1, 1))
        popup = Popup(
            title='Select a PDF',
            content=chooser,
            size_hint=(0.9, 0.9),
            auto_dismiss=False
        )

        # Accept the extra `touch` parameter here:
        def _on_selection(instance, selection, touch):
            if selection:
                self.viewer.load_pdf(selection[0])
                popup.dismiss()

        chooser.bind(on_submit=_on_selection)
        popup.open()

if __name__ == '__main__':
    PDFViewerApp().run()
