"""scm version"""

import os.path as pth

try:
    from setuptools_scm import get_version  # pylint: disable=import-error

    version = get_version(root=pth.join("..", "..", ".."), relative_to=__file__)
except Exception as exc:
    raise ImportError("setuptools_scm broken or not installed") from exc
