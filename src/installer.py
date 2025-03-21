import io
import logging
import os.path
import subprocess
import urllib.request
from shutil import which
from tkinter.messagebox import askyesnocancel
from typing import Any, Optional
from zipfile import ZipFile
from utils import open_file, is_windows


BEPINEX_URL = "https://api.github.com/repos/BepInEx/BepInEx/releases"
HOOKGEN_URL = "https://api.github.com/repos/harbingerofme/Bepinex.Monomod.HookGenPatcher/releases"
CHAUFFEUR_URL = "https://api.github.com/repos/alwaysintreble/Chauffeur/releases"


def launch_game(url: Optional[str] = None) -> None:
    """Check the game installation, then launch it"""

    def install_chauffeur() -> None:
        """Installs latest version of Chauffeur"""
        # can't use latest since courier uses pre-release tags
        courier_url = "https://api.github.com/repos/Brokemia/Courier/releases"
        latest_download = request_data(courier_url)[0]["assets"][-1]["browser_download_url"]

        with urllib.request.urlopen(latest_download) as download:
            with ZipFile(io.BytesIO(download.read()), "r") as zf:
                for member in zf.infolist():
                    zf.extract(member, path=game_folder)

        os.chdir(game_folder)
        # linux and mac handling
        if not is_windows:
            mono_exe = which("mono")
            if not mono_exe:
                # steam deck support but doesn't currently work
                messagebox("Failure", "Failed to install Courier", True)
                raise RuntimeError("Failed to install Courier")
                # # download and use mono kickstart
                # # this allows steam deck support
                # mono_kick_url = "https://github.com/flibitijibibo/MonoKickstart/archive/refs/heads/master.zip"
                # target = os.path.join(folder, "monoKickstart")
                # os.makedirs(target, exist_ok=True)
                # with urllib.request.urlopen(mono_kick_url) as download:
                #     with ZipFile(io.BytesIO(download.read()), "r") as zf:
                #         for member in zf.infolist():
                #             zf.extract(member, path=target)
                # installer = subprocess.Popen([os.path.join(target, "precompiled"),
                #                               os.path.join(folder, "MiniInstaller.exe")], shell=False)
                # os.remove(target)
            else:
                installer = subprocess.Popen([mono_exe, os.path.join(game_folder, "MiniInstaller.exe")], shell=False)
        else:
            installer = subprocess.Popen(os.path.join(game_folder, "MiniInstaller.exe"), shell=False)

        failure = installer.wait()
        if failure:
            messagebox("Failure", "Failed to install Courier", True)
            os.chdir(working_directory)
            raise RuntimeError("Failed to install Courier")
        os.chdir(working_directory)

        if courier_installed():
            messagebox("Success!", "Courier successfully installed!")
            return
        messagebox("Failure", "Failed to install Courier", True)
        raise RuntimeError("Failed to install Courier")

    def install_mod() -> None:
        """Installs latest version of the mod"""
        assets = request_data(MOD_URL)["assets"]
        if len(assets) == 1:
            release_url = assets[0]["browser_download_url"]
        else:
            for asset in assets:
                if "TheMessengerRandomizerAP" in asset["name"]:
                    release_url = asset["browser_download_url"]
                    break
            else:
                messagebox("Failure", "Failed to find latest mod download", True)
                raise RuntimeError("Failed to install Mod")

        mod_folder = os.path.join(game_folder, "Mods")
        os.makedirs(mod_folder, exist_ok=True)
        with urllib.request.urlopen(release_url) as download:
            with ZipFile(io.BytesIO(download.read()), "r") as zf:
                for member in zf.infolist():
                    zf.extract(member, path=mod_folder)

        messagebox("Success!", "Latest mod successfully installed!")


    from . import MessengerWorld
    game_folder = os.path.dirname(MessengerWorld.settings.game_path)
    working_directory = os.getcwd()
    if not courier_installed():
        should_install = askyesnocancel("Install Courier",
            "No Courier installation detected. Would you like to install now?")
        if not should_install:
            return
        logging.info("Installing Courier")
        install_chauffeur()
    if not mod_installed():
        should_install = askyesnocancel("Install Mod",
            "No randomizer mod detected. Would you like to install now?")
        if not should_install:
            return
        logging.info("Installing Mod")
        install_mod()
    else:
        latest = request_data(MOD_URL)["tag_name"]
        if available_mod_update(latest):
            should_update = askyesnocancel("Update Mod",
                f"New mod version detected. Would you like to update to {latest} now?")
            if should_update:
                logging.info("Updating mod")
                install_mod()
            elif should_update is None:
                return
    if not is_windows:
        if url:
            open_file(f"steam://rungameid/764790//{url}/")
        else:
            open_file("steam://rungameid/764790")
    else:
        os.chdir(game_folder)
        if url:
            subprocess.Popen([MessengerWorld.settings.game_path, str(url)])
        else:
            subprocess.Popen(MessengerWorld.settings.game_path)
        os.chdir(working_directory)
