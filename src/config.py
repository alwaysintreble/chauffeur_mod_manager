from utils import local_path


def validate_file_path(path: str) -> bool:
    valid_md5s = ["6067fb82a0775112ecce3cc67d3206df"]
    if path == local_path():
        return False
    try:
        with open(path, "rb", buffering=0) as f:
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
                raise ValueError(f"Invalid hash for {path}")
            f.seek(pos)
    except ValueError:
        return False
    else:
        return True
