try:
    try:
        from ._dev.scm_version import version
    except ImportError:
        from ._version import version
except Exception:
    import warnings

    warnings.warn(
        f'could not determine {__name__.split(".")[0]} package version; '
        "this indicates a broken installation"
    )
    del warnings

    version = "0.0.0"