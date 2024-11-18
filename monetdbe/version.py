# Single source of truth for the version number.
#
# The monetdbe versioning scheme is that the first two components of monetdbe's
# version number are taken from the underlying MonetDB version and the third is
# specific to monetdbe itself. The leading 11 of MonetDB's version number is
# skipped.
#
# For example, we might have monetdbe versions 51.3.0, 51.3.1 and 51.3.2 all
# based on MonetDB 11.51.3 (Aug2024) followed by 51.5.0 based on 11.51.5
# (Aug2024-SP1).
#
# Unreleased monetdb versions have a pre-release suffix, for example 'a0', see
# https://packaging.python.org/en/latest/specifications/version-specifiers/#pre-releases


version_tuple = (51, 5, 0)

version_suffix = 'a0'    # only empty on proper releases

__version__ = '.'.join(str(i) for i in version_tuple) + version_suffix


# does anybody use this?
version = __version__
monetdbe_version = __version__
