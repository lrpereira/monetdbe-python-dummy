"""
This is a build-time utility that will generate the monetdbe._lowlevel
CFFI bridging shared library.
"""
from pathlib import Path
import sys
from os import environ
import re
from cffi import FFI
from jinja2 import Template


# This is where we'll gather knowledge about this MonetDB.
#
# For example, version numbers and various flags used by the embed.h.j2 template
# (see below).
#
# It will also be written to branch.py for use at runtime.
info = {}


# Extract version info from the header files
monetdbe_include_path = environ.get('MONETDBE_INCLUDE_PATH')
if not monetdbe_include_path:
    print("\n\n**MONETDB**: MONETDBE_INCLUDE_PATH and MONETDBE_LIBRARY_PATH must be set")
monetdb_config_h = Path(monetdbe_include_path) / 'monetdb' / 'monetdb_config.h'
with open(monetdb_config_h) as f:
    config = f.read()
    for var in ['MONETDB_VERSION', 'MONETDB_RELEASE']:
        m = re.search(f'#define\\s+{var}\\s+"([^"]*)"', config)
        if m:
            info[var.lower()] = m[1]

monetdb_version = tuple(int(i) for i in info['monetdb_version'].split('.'))
if not 'monetdb_release' in info:
    info['monetdb_release'] = 'unreleased'


# Other info entries
info['win32'] = sys.platform == 'win32'
info['have_option_no_int128'] = monetdb_version >= (11, 50, 0)
info['have_load_extension'] = monetdb_version >= (11, 50, 0)


# Make the info available at runtime
branch_file = str(Path(__file__).parent / 'monet_info.py')
with open(branch_file, 'w') as f:
    print("# this file is created by the cffi interface builder.", file=f)
    print(f"INFO = {info!r}", file=f)


# Feed the info into the template to get the declarations we will
# give to the ffi builder.
embed_path = str(Path(__file__).resolve().parent / 'embed.h.j2')
with open(embed_path, 'r') as f:
    content = f.read()
    template = Template(content)
    cdeclarations = template.render(info)


# Read our C code
with open(Path(__file__).resolve().parent / "native_utilities.c") as f:
    source = f.read()


# Configure the FFI builder.
# We do not need to set library_dirs, that gets set from setup.py somehow.
ffibuilder = FFI()
ffibuilder.set_source("monetdbe._lowlevel", source=source, libraries=['monetdbe'])
ffibuilder.cdef(cdeclarations)


def build():
    ffibuilder.compile(verbose=True)


if __name__ == "__main__":
    build()
