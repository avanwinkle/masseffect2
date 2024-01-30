# Copyright 2023 Paradigm Tilt
"""Custom version checker for pt-sov-stable."""

from mpf.core.custom_code import CustomCode
from mpf._version import __version__ as mpfversion

REQUIRED_MPF_VERSION = "0.57.0.dev102"


class VersionChecker(CustomCode):

    """Check the current MPF version to ensure it's compatible."""

    def on_load(self):
        """Verify the correct version of MPF."""
        if mpfversion != REQUIRED_MPF_VERSION:
            raise ValueError(f"Found MPF version {mpfversion}, but {REQUIRED_MPF_VERSION} is required.")
