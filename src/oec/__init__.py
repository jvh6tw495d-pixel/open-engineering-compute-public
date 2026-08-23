"""Open Engineering Compute — executable, versioned and auditable engineering skills."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("open-engineering-compute")
except PackageNotFoundError:
    __version__ = "3.6.2"
