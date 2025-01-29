import json
import os
from typing import NamedTuple

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "ChauffeurManagerConfig.json")


class Config(NamedTuple):
    game_path: str


config_data: Config


def load_config():
    if not os.path.exists(CONFIG_PATH):
        from utils import open_filename, is_windows
        valid_md5s = ["6067fb82a0775112ecce3cc67d3206df"]
        res = open_filename("Select Game Executable", [("Program" if is_windows else "", [".exe"])])
        with open(res, "rb", buffering=0) as f:
            pos = f.tell()
            from hashlib import md5
            file_md5 = md5()
            block = bytearray(64*1024)
            view = memoryview(block)
            while n := f.readinto(view):  # type: ignore
                file_md5.update(view[:n])
            file_md5_hex = file_md5.hexdigest()
            for valid_md5 in valid_md5s:
                if valid_md5.lower() == file_md5_hex:
                    break
            else:
                raise ValueError(f"Invalid hash for {res}")
            f.seek(pos)
        global config_data
        config_data = Config(os.path.dirname(res))
        with open(CONFIG_PATH, "w") as f:
            json.dump(config_data._asdict(), f)
        return
    with open(CONFIG_PATH, "r") as f:
        config_data = Config(**json.load(f))


load_config()
