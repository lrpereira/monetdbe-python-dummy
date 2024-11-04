from setuptools import find_packages, setup
from sys import platform
import runpy
import os


version_file = os.path.join(os.path.dirname(__file__), "monetdbe", "version.py")
version_data = runpy.run_path(version_file)
version = version_data['__version__']

packages = find_packages(exclude=['tests', 'tests.test_lite'])


# is this still needed?
if platform == 'win32':
    package_data = {"monetdbe": ["*.dll"]}
else:
    package_data = {}

setup(
    # dynamic
    version = version,
    packages=packages,
    # invoke cffi
    cffi_modules=["monetdbe/_cffi/builder.py:ffibuilder"],
    # fine tune included files
    # package_data=package_data,
    # exclude_package_data= { "monetdbe._cffi": [ "*.h.j2", "*.c" ]}
)