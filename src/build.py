"""
Simple script to build the app using cx_Freeze since I couldn't get the other builders to work. :shrug:
Build by running `python build.py build_exe`
"""
import os
import shutil
import sysconfig
from pathlib import Path

import cx_Freeze

from utils import __version__


build_folder = Path("build", f"exe.{sysconfig.get_platform()}-{sysconfig.get_python_version()}")

exes = [cx_Freeze.Executable(
    script="main.py",
    target_name="Chauffeur Mod Manager.exe",
    base="Win32GUI",
)]

extra_data = ["data"]


class BuildCommand(cx_Freeze.command.build_exe.build_exe):
    def initialize_options(self) -> None:
        super().initialize_options()
        self.extra_data = []

    def install_file(self, path: Path) -> None:
        folder = build_folder
        if path.is_dir():
            folder /= path.name
            if folder.is_dir():
                shutil.rmtree(folder)
            shutil.copytree(path, folder, dirs_exist_ok=True)
        elif path.is_file():
            shutil.copy(path, folder)

    def run(self) -> None:
        super().run()

        # include_files doesn't exclude so custom version
        for src, dest in self.include_files:
            shutil.copyfile(src, build_folder / dest, follow_symlinks=False)

        from kivy_deps import sdl2, glew
        for folder in sdl2.dep_bins + glew.dep_bins:
            shutil.copytree(folder, Path(build_folder, "lib"), dirs_exist_ok=True)

        import kivy
        shutil.copytree(os.path.join(os.path.dirname(kivy.__file__), "data"),
                        build_folder / "data", dirs_exist_ok=True)

        for data in self.extra_data:
            self.install_file(Path(data))


cx_Freeze.setup(
    name="Chauffeur Mod Manager",
    version=__version__,
    description="Chauffeur Mod Manager",
    executables=exes,
    options={
        "build_exe": {
            "packages": ["kivy", "kivymd"],
            "excludes": ["numpy, Cython", "PySide2", "PIL", "pandas"],
            "optimize": 1,
            "build_exe": build_folder,
            "include_files": [],
            "extra_data": extra_data,
        }
    },
    cmdclass={
        "build_exe": BuildCommand,
    },
)
