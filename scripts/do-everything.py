#!/usr/bin/env python3

import argparse
from glob import glob
import importlib
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Optional, Tuple


# These will be set by check_monetdb
INC_DIR = None
LIB_DIR = None
BIN_DIR = None
DYN_SUFFIX = None


class Problem(Exception):
    pass


def check_venv(require_venv):
    if sys.prefix != sys.base_prefix:
        print(f'Running in venv:', sys.prefix)
    else:
        if require_venv:
            raise Problem('Expected to run in a venv (Virtual Environment). Activate one or pass --no-require-venv')
        else:
            print(f'Not running in a venv! Ignoring because --no-require-venv is set')


def check_monetdb():
    global INC_DIR, LIB_DIR, BIN_DIR, DYN_SUFFIX
    inc_env_var = 'MONETDBE_INCLUDE_PATH'
    lib_env_var = 'MONETDBE_LIBRARY_PATH'
    bin_env_var = 'MONETDBE_BINARY_PATH'
    inc_dir = os.getenv(inc_env_var, None)
    lib_dir = os.getenv(lib_env_var, None)
    bin_dir = os.getenv(bin_env_var, None)
    print(f'Found {inc_env_var}={inc_dir!r}')
    print(f'Found {lib_env_var}={lib_dir!r}')
    print(f'Found {bin_env_var}={bin_dir!r}')

    DYN_SUFFIX = (
        'dll' if platform.win32_ver()[0] else
        'dylib' if platform.mac_ver()[0] else
        'so'
    )
    print(f'Guessed DYN_SUFFIX={DYN_SUFFIX!r}')

    if inc_dir is None or lib_dir is None:
        raise Problem(f'${inc_env_var} and ${lib_env_var} must be set')
    INC_DIR = Path(inc_dir)
    LIB_DIR = Path(lib_dir)
    if bin_dir:
        BIN_DIR = Path(bin_dir)

    monetdbe_h_path = INC_DIR / 'monetdbe.h'
    if monetdbe_h_path.is_file():
        print(f'File {monetdbe_h_path} exists as expected')
    else:
        raise Problem(f'File {monetdbe_h_path} not found')

    lib_name = 'monetdbe.lib' if DYN_SUFFIX == 'dll' else f'libmonetdbe.{DYN_SUFFIX}'
    libmonetdbe_path = LIB_DIR / lib_name
    if libmonetdbe_path.is_file():
        print(f'File {libmonetdbe_path} exists as expected')
    else:
        raise Problem(f'File {libmonetdbe_path} not found')


def check_build_dependencies():
    required = ['build']
    if DYN_SUFFIX == 'so':
        required.append('repairwheel')
    for req in required:
        try:
            print(f'Looking for module {req!r}', end='', flush=True)
            m = importlib.import_module(req)
            print(f': version {m.__version__}')
        except ModuleNotFoundError as e:
            raise Problem(f'{e}, maybe install it with: pip install -r requirements.txt')
    print('Dependencies OK')


def run_build_frontend():
    deleted_previous = False
    for x in [*glob('dist/*.whl'), *glob('dist/*.tar.gz')]:
        if not deleted_previous:
            print('Deleting leftovers from a previous run')
            deleted_previous = True
        print(f'Deleting {x}')
        os.unlink(x)

    import build.__main__
    print('---------------------  Building sdist and wheel  ---------------------')
    build.__main__.main([], 'do-everything: python -m build')
    print('------------------------  Built sdist and wheel  ---------------------')
    for x in glob('dist/*'):
        stats = os.stat(x)
        print(f'Produced {x} ({stats.st_size} bytes)')


def post_process(destdir: str, manylinux: Optional[Tuple[int, int]]):
    print('Post processing.')
    try:
        os.mkdir(destdir)
        print(f'Created directory {destdir!r}')
    except FileExistsError:
        pass

    copied = False
    for whl in glob('dist/*.tar.gz'):
        print(f'Copy {whl!r} to {destdir!r}')
        shutil.copy(whl, destdir)
        copied = True
    if not copied:
        raise Problem(f'No .tar.gz files found in dist/')

    # Where are the shared libraries? Except for Windows they are usually in the
    # lib dir. On Windows, they are in ..\MonetDB5\bin. However, because
    # mclient.bat etc are in ..\MonetDB5, BIN_DIR=..\MonetDB5.
    # So we have to add the \bin suffix here.
    if DYN_SUFFIX == 'dll':
        so_dir = BIN_DIR / 'bin'
    else:
        so_dir = LIB_DIR
    so_pattern = str(so_dir / f'*monetdbe.{DYN_SUFFIX}')
    if not glob(so_pattern):
        raise Problem(f'Looking for shared libs, no match found for {so_pattern}')


    copied = False
    with tempfile.TemporaryDirectory()as tmpdir:
        dist_wheel_pattern = str(Path('dist' ) / '*.whl')
        for whl in glob(dist_wheel_pattern):
            # Originally we had separate branches to run auditwheel on Linux,
            # delocate on Mac and whatever on Windows but repairwheel is supposed to
            # be able to handle everything.
            cmd = [
                sys.executable, '-m', 'repairwheel',
                whl,
                '-o', tmpdir,
                '-l', str(so_dir),
            ]
            print('------------------------  Making wheel self-contained  -----------------------')
            print(f'Running:', shlex.join(cmd))
            subprocess.check_call(cmd)
            print('---------------------  Done making wheel self-contained  ---------------------')
            copied = True
        if not copied:
            raise Problem(f'No .whl files found in dist/')
        tmp_wheel_pattern = str(Path(tmpdir) / '*.whl')
        for whl in glob(tmp_wheel_pattern):
            m = re.search('manylinux_(\d+)_(\d+)', whl)
            if m and manylinux:
                major = int(m[1])
                minor = int(m[2])
                if (major, minor) > manylinux:
                    raise Problem(f'Have --manylinux={manylinux[0]}_{manylinux[1]} but found {m[0]}')
            print(f'Moving {Path(whl).name} to {destdir}/')
            shutil.move(whl, destdir)



argparser = argparse.ArgumentParser()
argparser.add_argument('-d', '--dest-dir', required=True,
                       help='Directory to leave the wheels and source distribution')
default_manylinux_ver = '2_28'
argparser.add_argument('--manylinux', default=default_manylinux_ver,
                       help=f'Version of manylinux to target, default {default_manylinux_ver}')
argparser.add_argument('--no-require-venv', action='store_true')


def main(args):

    if args.manylinux:
        major, minor = re.split('[_.]', args.manylinux)
        manylinux = (int(major), int(minor))
    else:
        manylinux

    print('This is do-everything.py')
    print(f'Python is {sys.executable!r} ({sys.version})')

    check_venv(not args.no_require_venv)
    check_monetdb()
    check_build_dependencies()

    print()
    run_build_frontend()
    print()

    post_process(args.dest_dir, manylinux)


if __name__ == "__main__":
    try:
        args = argparser.parse_args()
        sys.exit(main(args) or 0)
    except Problem as e:
        print()
        print(f'Error: {e}')
        sys.exit(1)