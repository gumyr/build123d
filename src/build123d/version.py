"""
Export a version string.
"""

try:
    try:
        from ._dev.scm_version import version  # pylint: disable=unused-import
    except ImportError:
        from ._version import version
except Exception:  # pylint: disable=broad-exception-caught
    import warnings

    warnings.warn(
        f'could not determine {__name__.split(".", maxsplit=1)[0]} package version; '
        "this indicates a broken installation"
    )
    del warnings

    version = "0.0.0"  # pylint: disable=invalid-name
