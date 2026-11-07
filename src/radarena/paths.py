"""Resolve dataset paths without rewriting checksummed historical artifacts."""

from pathlib import Path


def resolve_data_path(value: str | Path) -> Path:
    """Rebase known dataset paths into the checkout used as the working directory.

    Old runs recorded absolute paths from their original machine. Only paths
    inside the recognized IU dataset layouts are translated. Other paths retain
    their normal behavior, including fixture paths and missing-file errors.
    """
    path = Path(value)
    parts = path.parts
    for index, part in enumerate(parts):
        if part != "data":
            continue
        suffix = parts[index + 1:]
        if suffix[:3] == ("archive (1)", "images", "images_normalized"):
            relative = Path("data/raw/iu_xray/images", *suffix[3:])
        elif suffix[:1] == ("archive (1)",):
            relative = Path("data/raw/iu_xray", *suffix[1:])
        elif suffix[:2] == ("raw", "iu_xray"):
            relative = Path("data", *suffix)
        else:
            continue
        if ".." not in relative.parts and relative.is_file():
            return relative
        # Upstream ZIPs may retain the images/images_normalized directory.
        if relative.parts[:4] == ("data", "raw", "iu_xray", "images") and ".." not in relative.parts:
            nested = Path("data/raw/iu_xray/images/images_normalized", *relative.parts[4:])
            if nested.is_file():
                return nested
    return path


def portable_data_path(value: str | Path) -> str:
    """Store new paths relative to the working checkout where possible."""
    path = Path(value).resolve()
    try:
        return path.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return str(path)
