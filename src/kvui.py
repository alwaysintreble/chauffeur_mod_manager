
from kivy.uix.floatlayout import FloatLayout
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDTextButton, MDIconButton
from kivymd.uix.screen import MDScreen
from kivymd.uix.scrollview import MDScrollView


class MainApp(MDApp):
    title = "Chauffeur Mod Manager"
    container: FloatLayout
    navigation: MDBoxLayout
    grid: MDGridLayout
    button_layout: MDScrollView

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Yellow"
        self.container = FloatLayout()
        self.navigation = MDBoxLayout()
        menu_icons = {
            "Launch Game": "play",
            "Installed Mods": "controller",
            "Explore Mods": "desktop-classic",
            "Settings": "wrench",
        }
        screen = MDScreen(
            MDRaisedButton(MDTextButton(text="Hello, World!"), pos_hint={"center_x": 0.5, "center_y": 0.5}),
        )
        return screen


MainApp().run()
