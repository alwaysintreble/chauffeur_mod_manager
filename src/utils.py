import logging
import os
import subprocess
import sys
from typing import Any, Iterable, NamedTuple

import requests


is_linux = sys.platform.startswith("linux")
is_macos = sys.platform == "darwin"
is_windows = sys.platform in ("win32", "cygwin", "msys")


class Version(NamedTuple):
    major: int
    minor: int
    patch: int


def tuplize_version(version: str) -> Version:
    return Version(*(int(piece, 10) for piece in version.split(".")))


def chauffeur_installed() -> bool:
    """Check if Chauffeur is installed"""
    from config import config_data
    bepin_folder = os.path.join(config_data.game_path, "BepInEx")
    return (os.path.exists(bepin_folder) and
            os.path.exists(os.path.join(bepin_folder, "plugins")) and
            os.path.exists(os.path.join(bepin_folder, "plugins", "MMHOOK")) and
            os.path.exists(os.path.join(bepin_folder, "plugins", "Chauffeur")))


def is_kivy_running() -> bool:
    if "kivy" in sys.modules:
        from kivy.app import App
        return App.get_running_app() is not None
    return False


def _mp_open_filename(res: "multiprocessing.Queue[str | None]", *args: Any) -> None:
    if is_kivy_running():
        raise RuntimeError("kivy should not be running in multiprocess")
    res.put(open_filename(*args))


def open_file(filename: "str | pathlib.Path") -> None:
    if is_windows:
        os.startfile(filename)
    else:
        from shutil import which
        open_command = which("open") if is_macos else (which("xdg-open") or which("gnome-open") or which("kde-open"))
        assert open_command, "Didn't find program for open_file! Please report this together with system details."
        subprocess.call([open_command, filename])


def open_filename(title: str, filetypes: Iterable[tuple[str, Iterable[str]]], suggest: str = "") -> str | None:
    def run(*args: str) -> int | None:
        return subprocess.run(args, capture_output=True, text=True).stdout.split("\n", 1)[0] or None

    if is_linux:
        # prefer native dialog
        from shutil import which
        kdialog = which("kdialog")
        if kdialog:
            k_filters = '|'.join((f'{text} (*{" *".join(ext)})' for (text, ext) in filetypes))
            return run(kdialog, f"--title={title}", "--getopenfilename", suggest or ".", k_filters)
        zenity = which("zenity")
        if zenity:
            z_filters = (f'--file-filter={text} ({", ".join(ext)}) | *{" *".join(ext)}' for (text, ext) in filetypes)
            selection = (f"--filename={suggest}",) if suggest else ()
            return run(zenity, f"--title={title}", "--file-selection", *z_filters, *selection)

    # fall back to tk
    try:
        import tkinter
        import tkinter.filedialog
    except Exception as e:
        logging.error('Could not load tkinter, which is likely not installed. '
                      f'This attempt was made because open_filename was used for "{title}".')
        raise e
    else:
        if is_macos and is_kivy_running():
            # on macOS, mixing kivy and tk does not work, so spawn a new process
            # FIXME: performance of this is pretty bad, and we should (also) look into alternatives
            from multiprocessing import Process, Queue
            res: "Queue[typing.Optional[str]]" = Queue()
            Process(target=_mp_open_filename, args=(res, title, filetypes, suggest)).start()
            return res.get()
        try:
            root = tkinter.Tk()
        except tkinter.TclError:
            return None  # GUI not available. None is the same as a user clicking "cancel"
        root.withdraw()
        return tkinter.filedialog.askopenfilename(title=title, filetypes=((t[0], ' '.join(t[1])) for t in filetypes),
                                                  initialfile=suggest or None)


def request_data(request_url: str) -> Any:
    """Fetches json response from given url"""
    logging.info(f"requesting {request_url}")
    response = requests.get(request_url)
    if response.status_code == 200:  # success
        data = response.json()
    else:
        raise RuntimeError(f"Unable to fetch data. (status code {response.status_code})")
    return data


# def get_available_mods() -> dict[str, str]:
#     """Get available mods from repo manifest. Returned as [name, url]"""
    


def available_mod_update(mod_name: str, latest_version: str) -> bool:
    """Check if there's an available update for this mod"""
    from win32api import GetFileVersionInfo, LOWORD, HIWORD
    from config import config_data
    latest_version = latest_version.lstrip("v")
    installed_version_info = GetFileVersionInfo(
        os.path.join(config_data.game_path, "BepInEx", "plugins", f"{mod_name}", f"{mod_name}.dll"), "\\")
    ms = installed_version_info["FileVersionMS"]
    ls = installed_version_info["FileVersionLS"]
    version = (HIWORD(ms), LOWORD(ms), HIWORD(ls))
    installed_version = ".".join(str(i) for i in version)

    logging.info(f"Installed version: {installed_version}. Latest version: {latest_version}")
    return tuplize_version(latest_version) > tuplize_version(installed_version)


def get_installed_mods() -> list[str]:
    """Get list of installed mods"""
    from config import config_data
    mods_path = os.path.join(config_data.game_path, "BepInEx", "plugins")
    return [d for d in os.listdir(mods_path) if os.path.isdir(d) and d not in ("Chauffeur", "MMHOOK")]
