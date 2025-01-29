from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDTextButton
from kivymd.uix.screen import MDScreen


class MainApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Yellow"
        screen = MDScreen(
            MDRaisedButton(icon="plus", text="Button", height=2, pos_hint={"x": 0.5, "y": 0.5}),
        )
        return screen


MainApp().run()
