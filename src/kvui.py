from __future__ import annotations

import os.path
import subprocess
from typing import Any, NamedTuple

from kivy.lang import Builder
from kivy.properties import ConfigParser, ObjectProperty, StringProperty
from kivy.uix.settings import SettingsWithNoMenu, SettingsWithSidebar, SettingsWithSpinner, SettingsWithTabbedPanel
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.card import MDCard
from kivymd.uix.navigationbar import MDNavigationItem
from kivymd.uix.relativelayout import MDRelativeLayout
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import (
    MDSnackbar, MDSnackbarActionButton, MDSnackbarActionButtonText,
    MDSnackbarButtonContainer, MDSnackbarCloseButton, MDSnackbarSupportingText, MDSnackbarText,
)

from src.config import validate_file_path
from src.utils import (
    chauffeur_installed, get_available_mods, get_installed_mod_version, get_installed_mods, get_remote_mod_version,
    install_bepin, install_mod, is_windows, open_file,
    tuplize_version,
)
from utils import __version__, local_path


class ThemedApp(MDApp):
    def set_colors(self) -> None:
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Yellow"


class ChauffeurSnackbar(MDSnackbar):
    text = StringProperty()
    action_text = StringProperty()


class ChauffeurNavigationItem(MDNavigationItem):
    icon = StringProperty()
    text = StringProperty()


class ChauffeurScreen(MDScreen):
    pass


class ModCard(MDCard):
    text = StringProperty()
    description = StringProperty()
    icon = StringProperty()
    mod: ModEntry

    def __init__(self, mod_entry: ModEntry, **kwargs):
        self.mod = mod_entry
        super().__init__(**kwargs)


class ModCardLayout(MDRelativeLayout):
    text = StringProperty()
    description = StringProperty()
    icon = StringProperty()


class InstalledModCard(ModCard):
    pass


class RemoteModCard(ModCard):
    pass


class SettingsCard(MDCard):
    pass


class ChauffeurApp(ThemedApp):
    title: str = f"Chauffeur Mod Manager v{__version__}"
    icon: str = r"assets/icon.png"
    settings_cls = SettingsWithSpinner
    use_kivy_settings = False
    top_screen: MDBoxLayout = ObjectProperty(None)
    installed_mods_layout: MDBoxLayout = ObjectProperty(None)
    available_mods_layout: MDBoxLayout = ObjectProperty(None)
    index_data: dict[str, dict[str, str]]
    installed_mods: list[ModEntry]
    available_mods: list[ModEntry]
    game_path: str

    def build(self):
        self.top_screen = Builder.load_file(local_path("data", "manager.kv"))
        self.set_colors()
        # self.top_screen.md_bg_color = self.theme_cls.backgroundColor
        self.installed_mods_layout = self.top_screen.ids.install.layout
        self.available_mods_layout = self.top_screen.ids.explore.layout
        self.top_screen.ids.install.layout.scroll_y = 0
        self.top_screen.ids.explore.layout.scroll_y = 0
        self.installed_mods = []
        self.available_mods = []

        return self.top_screen

    def build_config(self, config: ConfigParser) -> None:
        config.setdefaults("configuration", {"path": local_path()})

    def build_settings(self, settings: SettingsWithSpinner):
        settings.add_json_panel("Chauffeur Settings", self.config, local_path("data", "settings.json"))
        pass

    def on_config_change(self, config: ConfigParser, section: str, key: str, value: Any) -> None:
        if key == "path":
            if not validate_file_path(value):
                ChauffeurSnackbar(
                    text="Invalid path. Make sure to select the game executable.",
                    action_text="Settings",
                ).open()
            else:
                self.check_mods()
        print(type(value))
        pass

    def engage_snack(self, snack_action: str) -> None:
        if snack_action == "Settings":
            self.open_settings()
        elif snack_action == "Install":
            self.install_chauffeur()

    def launch_game(self, caller: MDButton):
        if validate_file_path(self.game_path):
            if is_windows:
                os.startfile(self.game_path)
        else:
            self.on_missing_path()

    def check_mods(self) -> bool:
        if not chauffeur_installed(os.path.dirname(self.game_path)):
            MDSnackbar(
                MDSnackbarText(text="Chauffeur not installed.", pos_hint={"center_y": 0.5}),
                MDSnackbarButtonContainer(
                    MDSnackbarActionButton(
                        MDSnackbarActionButtonText(text="Install"),
                        on_release=self.engage_snack("Install")
                    ),
                    pos_hint={"center_y": 0.5},
                ),
                orientation="horizontal",
                pos_hint={"center_x": 0.5, "center_y": 0.2},
                size_hint={0.4, None},
                background_color=self.theme_cls.errorColor,
                auto_dismiss=False,
                duration=300,
            ).open()
            return False
        if self.installed_mods or self.available_mods:
            self.installed_mods_layout.clear_widgets()
            self.available_mods_layout.clear_widgets()
        else:
            self.build_mod_data()
        for mod in self.installed_mods:
            self.installed_mods_layout.add_widget(
                InstalledModCard(
                    mod,
                    text=mod.name,
                    description=mod.description,
                    icon=mod.icon,
                )
            )
        for mod in self.available_mods:
            self.available_mods_layout.add_widget(
                RemoteModCard(
                    mod,
                    text=mod.name,
                    description=mod.description,
                    icon=mod.icon,
                )
            )
        return True

    def build_mod_data(self) -> None:
        index_data = get_available_mods()
        currently_installed = get_installed_mods(os.path.dirname(self.game_path))
        if currently_installed:
            # build mod entries using the index data and drop them from the index
            to_drop = []
            for mod, data in index_data.items():
                if data["name"] in currently_installed or mod in currently_installed:
                    # check if there are any new versions available
                    try:
                        # try to lookup by the name
                        installed_version = get_installed_mod_version(data["name"], os.path.dirname(self.game_path))
                    except FileNotFoundError:
                        # fallback to uuid
                        installed_version = get_installed_mod_version(mod, os.path.dirname(self.game_path))
                    latest_version, version_data = get_remote_mod_version(data)
                    changelog = []
                    if tuplize_version(installed_version) < tuplize_version(latest_version["mod_version"]):
                        # compile all the changelogs between install and latest together
                        for version in version_data:
                            if tuplize_version(version["mod_version"]) > tuplize_version(installed_version):
                                changelog.extend(version["changelog"])
                    self.installed_mods.append(
                        create_mod_entry(
                            mod,
                            data,
                            latest_version,
                            changelog,
                        )
                    )
                    to_drop.append(mod)
            for name in to_drop:
                del index_data[name]
        if index_data:
            # build mod entries using the index data
            for mod, data in index_data.items():
                latest_version, version_info = get_remote_mod_version(data)
                self.available_mods.append(
                    create_mod_entry(
                        mod,
                        data,
                        latest_version,
                    )
                )

    def download_mod(self, mod_card: ModCardLayout) -> None:
        mod_entry: ModEntry = mod_card.parent.mod
        install_mod(
            os.path.dirname(self.game_path),
            mod_entry.name,
            mod_entry.download_url,
            mod_entry.sha256,
        )
        MDSnackbar(
            MDSnackbarText(text=f"{mod_entry.name} installed!", pos_hint={"center_x": 0.5, "center_y": 0.5}),
            pos_hint={"center_x": 0.5, "center_y": 0.2},
            size_hint={0.26, None},
            background_color=self.theme_cls.errorColor,
        ).open()
        self.installed_mods.append(mod_entry)
        self.available_mods.remove(mod_entry)
        self.check_mods()

    def on_start(self):
        self.game_path = self.config.get("configuration", "path")
        if validate_file_path(self.game_path):
            self.check_mods()
        else:
            self.on_missing_path()

    def on_missing_path(self) -> None:
        ChauffeurSnackbar(text="Game path not found.", action_text="Settings").open()

    def install_chauffeur(self):
        install_bepin(os.path.dirname(self.game_path))
        install_mod(
            os.path.dirname(self.game_path),
            "MMHOOK",
            "https://github.com/harbingerofme/Bepinex.Monomod.HookGenPatcher/releases/download/1.2.1/Release.zip",
            )
        install_mod(
            os.path.dirname(self.game_path),
            "Chauffeur",
            "https://github.com/alwaysintreble/Chauffeur/releases/download/v0.2.0/Chauffeur.dll",
            )
        self.check_mods()

class ModEntry(NamedTuple):
    uuid: str
    name: str
    description: str
    author: str
    homepage: str
    icon: str
    latest_version: str
    download_url: str
    sha256: str
    changelog: list[str]

    def get_icon(self):
        pass

def create_mod_entry(
        mod_uuid: str,
        mod_data: dict[str, str],
        latest_version: dict[str, str],
        changelog: list[str] | None = None
        ) -> ModEntry:
    changelog = changelog or []
    return ModEntry(
        mod_uuid,
        mod_data["name"],
        mod_data["description"],
        mod_data["author"],
        mod_data["homepage"],
        mod_data.get("icon_url", ""),
        latest_version["mod_version"],
        latest_version["download_url"],
        latest_version["sha256"],
        changelog,
    )

ChauffeurApp().run()
