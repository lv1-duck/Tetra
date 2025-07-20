from kivy.uix.boxlayout import BoxLayout


class ViewerScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # TODO: initialize page index, PDF renderer

    def load_pdf(self, path):
        # TODO: render first page and display
        pass

    def show_next(self):
        # TODO: navigate to next page
        pass

    def show_previous(self):
        # TODO: navigate to previous page
        pass