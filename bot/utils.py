import os
import pkgutil
from collections.abc import Iterator
from pathlib import Path


def search_directory(path: str) -> Iterator[str]:
    """Walk through a directory and yield all modules.

    Parameters
    ----------
    path: :class:`str`
        The path to search for modules

    """
    relpath = os.path.relpath(path)  # relative and normalized
    if ".." in relpath:
        msg = "Modules outside the cwd require a package to be specified"
        raise ValueError(msg)

    abspath = Path(path).resolve()
    if not Path(relpath).exists():
        msg = f"Provided path '{abspath}' does not exist"
        raise ValueError(msg)
    if not Path(relpath).is_dir():
        msg = f"Provided path '{abspath}' is not a directory"
        raise ValueError(msg)

    prefix = relpath.replace(os.sep, ".")
    if prefix in ("", "."):
        prefix = ""
    else:
        prefix += "."

    for _, name, ispkg in pkgutil.iter_modules([path]):
        if ispkg:
            yield from search_directory(Path(path) / name)
        else:
            yield prefix + name
