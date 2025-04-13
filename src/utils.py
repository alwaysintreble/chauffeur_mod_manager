import hashlib
import io
import logging
import mimetypes
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from typing import Any, Iterable, NamedTuple
from zipfile import ZipFile

import requests


__version__ = "0.0.1"

is_linux = sys.platform.startswith("linux")
is_macos = sys.platform == "darwin"
is_windows = sys.platform in ("win32", "cygwin", "msys")


class Version(NamedTuple):
    major: int
    minor: int
    patch: int


def tuplize_version(version: str) -> Version:
    return Version(*(int(piece, 10) for piece in version.split(".")))


def chauffeur_installed(game_path: str) -> bool:
    """Check if Chauffeur is installed"""
    bepin_folder = os.path.join(game_path, "BepInEx")
    return (os.path.exists(bepin_folder) and
            os.path.exists(os.path.join(bepin_folder, "plugins")) and
            os.path.exists(os.path.join(bepin_folder, "plugins", "MMHOOK")) and
            os.path.exists(os.path.join(bepin_folder, "plugins", "Chauffeur")))


def open_file(filename: "str | pathlib.Path") -> None:
    if is_windows:
        os.startfile(filename)
    else:
        from shutil import which
        open_command = which("open") if is_macos else (which("xdg-open") or which("gnome-open") or which("kde-open"))
        assert open_command, "Didn't find program for open_file! Please report this together with system details."
        subprocess.call([open_command, filename])


def request_data(request_url: str) -> Any:
    """Fetches json response from given url"""
    logging.info(f"requesting {request_url}")
    response = requests.get(request_url)
    if response.status_code == 200:  # success
        return response.json()
    raise RuntimeError(f"Unable to fetch data. (status code {response.status_code})")


def get_available_mods() -> dict[str, dict[str, str]]:
    """Get available mods from repo manifest. Returned as [name, url]"""
    available_mods_url = "https://raw.githubusercontent.com/alwaysintreble/chauffeur_mod_manager/refs/heads/modlist/available-mods.json"
    return request_data(available_mods_url)


def install_mod(game_path: str, mod_name: str, download_url: str, expected_hash: str = "") -> None:
    with urllib.request.urlopen(download_url) as download:
        file_type, _ = mimetypes.guess_type(download_url)
        file_data = download.read()
        file_bytes = io.BytesIO(file_data)
        # if expected_hash:
        #     sha256_hash = hashlib.sha256()
        #     with open(file_data, "rb") as f:
        #         for byte_block in iter(lambda: f.read(4096), b""):
        #             sha256_hash.update(byte_block)
        #         if not sha256_hash.hexdigest() == expected_hash:
        #             raise ValueError("File hash does not match expected.")
        destination_folder = os.path.join(game_path, "BepInEx", "plugins", mod_name)
        os.makedirs(destination_folder, exist_ok=True)
        if zipfile.is_zipfile(file_bytes):
            with ZipFile(file_bytes, "r") as zip_file:
                for member in zip_file.infolist():
                    new_name = member.filename.split("/")[-1]
                    with zip_file.open(member) as source_file:
                        with open(os.path.join(destination_folder, new_name), "wb") as target_file:
                            target_file.write(source_file.read())
        else:
            with open(os.path.join(destination_folder, download_url.split("/")[-1]), "wb") as f:
                shutil.copyfileobj(download, f)


def install_bepin(game_path: str) -> None:
    bepin_url: str = "https://api.github.com/repos/BepInEx/BepInEx/releases"
    data = request_data(bepin_url)
    for release in data:
        if release["prerelease"]:
            continue
        break
    else:
        raise ValueError
    assets = release["assets"]
    for asset in assets:
        if "win_x64" not in asset["name"]:
            continue
        break
    else:
        raise ValueError
    download_url = asset["browser_download_url"]

    with urllib.request.urlopen(download_url) as download:
        with ZipFile(io.BytesIO(download.read()), "r") as zip_file:
            for member in zip_file.infolist():
                zip_file.extract(member, path=game_path)
    os.makedirs(os.path.join(game_path, "BepInEx", "plugins"), exist_ok=True)


def get_installed_mod_version(mod_name: str, game_path: str) -> str:
    from win32api import GetFileVersionInfo, LOWORD, HIWORD

    mod_path = os.path.join(game_path, "BepInEx", "plugins", mod_name)
    possible_files = [file for file in os.listdir(mod_path) if file.endswith(".dll")]
    potential_name = "".join(mod_name.split(" ")) + ".dll"
    if len(possible_files) == 1:
        installed_version_info = GetFileVersionInfo(
            os.path.join(mod_path, possible_files[0]),
            "\\",
        )
    elif potential_name in possible_files:
        installed_version_info = GetFileVersionInfo(
            os.path.join(mod_path, potential_name),
            "\\",
        )
    else:
        raise ValueError("I'm not sure what to do here without adding fuzzy matching")
    ms = installed_version_info["FileVersionMS"]
    ls = installed_version_info["FileVersionLS"]
    version = (HIWORD(ms), LOWORD(ms), HIWORD(ls))
    installed_version = ".".join(str(i) for i in version)

    return installed_version


def get_remote_mod_version(mod_data: dict[str, str]) -> tuple[dict[str, str], list[dict[str, str]]]:
    versions_url = mod_data["versions_url"]
    version_info = request_data(versions_url)["versions"]
    return version_info[0], version_info


def available_mod_update(mod_name: str, game_path: str, latest_version: str) -> bool:
    """Check if there's an available update for this mod"""
    latest_version = latest_version.lstrip("v")
    installed_version = get_installed_mod_version(mod_name, game_path)

    logging.info(f"Installed version: {installed_version}. Latest version: {latest_version}")
    return tuplize_version(latest_version) > tuplize_version(installed_version)


def get_installed_mods(path: str) -> list[str]:
    """Get list of installed mods"""
    mods_path = os.path.join(path, "BepInEx", "plugins")
    return [d for d in os.listdir(mods_path) if d not in ("Chauffeur", "MMHOOK") and os.path.isdir(os.path.join(mods_path, d))]


def local_path(*path: str) -> str:
    if hasattr(local_path, "cached_path"):
        pass
    elif hasattr(sys, "_MEIPASS"):
        local_path.cached_path = sys._MEIPASS
    else:
        import __main__
        if hasattr(__main__, "__file__") and os.path.isfile(__main__.__file__):
            local_path.cached_path = os.path.dirname(os.path.abspath(__main__.__file__))
        else:
            local_path.cached_path = os.path.abspath(".")
    return os.path.join(local_path.cached_path, *path)  # type: ignore



class Config(NamedTuple):
    game_path: str
