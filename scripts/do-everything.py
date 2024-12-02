#!/usr/bin/env python3


import argparse
import contextlib
import glob
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv


DESCR = """
Build a Python-MonetDBe distribution for the current platform. This is like
running `python -m build` except that all of MonetDB gets embedded in the
resulting .whl file. (The output of `python -m build` will only work on
systems that have MonetDB already installed.)
"""
EPILOG = """
By default, this tool creates a fresh virtual environment in which it
installs its own dependencies. This can be inhibited with --no-isolation.
"""


ON_WIN32 = not not platform.win32_ver()[0]
ON_MACOS = not not platform.mac_ver()[0]
ON_UNIX = not ON_WIN32 and not ON_MACOS
EXAMPLE_HEADER = 'monetdbe.h'
EXAMPLE_LIB = 'monetdbe.lib' if ON_WIN32 else 'libmonetdbe.dylib' if ON_MACOS else 'libmonetdbe.so'
EXAMPLE_SO = 'monetdbe.dll' if ON_WIN32 else EXAMPLE_LIB


class Problem(Exception):
    pass


# Overridde by main()
SCRATCH_DIR = None
# Overridden by find_directories()
INC_DIR = None
LIB_DIR = None
DYN_DIR = None


def find_directories(args):
    global INC_DIR, LIB_DIR, DYN_DIR

    def get_setting(flagname, envvar, required=True):
        flag = getattr(args, flagname, None)
        if flag is not None:
            return flag
        var = os.getenv(envvar)
        if var is not None:
            return var
        if required:
            raise Problem(f'At least one of --{flagname.replace("_", "-")} and {envvar} must be set')

    INC_DIR = get_setting('inc_dir', 'MONETDBE_INCLUDE_PATH')
    LIB_DIR = get_setting('lib_dir', 'MONETDBE_LIBRARY_PATH')
    DYN_DIR = get_setting('dyn_dir', 'MONETDBE_DYNAMIC_PATH', required=False)

    def check_path(dir, filename, thing, sources):
        please_set = f'Please set one of {" or ".join(sources)}'
        if dir is None:
            raise Problem(please_set)
        full_path = os.path.join(dir, filename)
        if os.path.exists(full_path):
            print(f'Found {thing} {full_path}')
        else:
            print(f'Could not find {thing} {full_path}')
            raise Problem(f'Could not find {filename} in {dir}. {please_set}')

    check_path(INC_DIR, EXAMPLE_HEADER, 'header', ['--inc-dir', 'MONETDBE_INCLUDE_PATH'])
    check_path(LIB_DIR, EXAMPLE_LIB, 'lib', ['--lib-dir', 'MONETDBE_LIBRARY_PATH'])

    if DYN_DIR is not None:
        candidates = [DYN_DIR]
    else:
        candidates = [LIB_DIR]
        head, tail = os.path.split(LIB_DIR)
        if tail == 'lib':
            candidates.append(os.path.join(head, 'bin'))
    exception = None
    for candidate in candidates:
        try:
            check_path(candidate, EXAMPLE_SO, 'dyn', ['--dyn-dir', 'MONETDBE_DYNAMIC_PATH'])
            DYN_DIR = candidate
            break
        except Problem as problem:
            if exception is None:
                exception = problem
                continue
    else:
        assert exception is not None
        raise exception


def initialize_scratch_dir(dir, delete: bool):
    """
    Create or clear the given directory, leaving a marker file to indicate that it was created by us.
    Only delete files if such a marker file is present.
    """
    marker_file = 'build-monetdbe.here'
    marker_path = os.path.join(dir, marker_file)

    # There are three valid cases:
    # 1. the directory does not exist and we create it
    # 2. it exists but is empty
    # 3. it exists and contains our marker file, in which case we may delete
    #    everything else

    # First check for case 3
    if os.path.isfile(marker_path):
        print(f'Using existing scratch directory {dir}')
        if delete:
            for entry in os.listdir(dir):
                path = os.path.join(dir, entry)
                if os.path.samefile(path, marker_path):
                    continue
                if os.path.isdir(path):
                    print(f' - deleting {entry}/')
                    shutil.rmtree(path)
                else:
                    print(f' - deleting {entry}')
                    os.remove(path)
        # Directory exists and is empty except for the marker file, we're done
        return

    try:
        os.mkdir(dir)
        # We have Case 1: newly created
    except FileExistsError:
        # It's still ok as long as it's an empty directory
        if not os.path.isdir(dir) or os.listdir(dir) != []:
            raise Problem(f'Scratch directory not empty: {dir}')
        # We have Case 2: a preexisting empty directory

    # Now create the marker file
    with open(marker_path, 'x'):
        pass
    print(f'Initialized scratch directory {dir}')


def restart_in_venv():
    venv_dir = os.path.join(SCRATCH_DIR, 'venv')
    print(f'Creating venv {venv_dir}')
    venv.create(venv_dir, clear=True, with_pip=True)
    interpreter = os.path.join(
        venv_dir,
        'Scripts' if ON_WIN32 else 'bin',
        'python.exe' if ON_WIN32 else 'python'
    )
    new_cmdline = [
        interpreter,
        *sys.argv,
        "--inner", "--install-dependencies"
    ]
    new_env = os.environ.copy()
    new_env['VIRTUAL_ENV'] = venv_dir
    print(f'Restarting in venv {venv_dir}')
    print(f'Inner command:', shlex.join(new_cmdline))
    print('=' * 72)
    return subprocess.call(new_cmdline, env=new_env)


def project_root(*append):
    root_scripts_me = sys.argv[0]                      # ../Python-MonetDBe/scripts/do-everything.py
    root_scripts = os.path.dirname(root_scripts_me)    # ../Python-MonetDBe/scripts
    root = os.path.dirname(root_scripts)               # ../Python-MonetDBe
    if append:
        return os.path.join(root, *append)
    else:
        return root


def run_module(mod, *args, **envs):
    cmdline = [sys.executable, '-m', mod, *[str(a) for a in args]]
    new_env = os.environ.copy()
    new_env.update(**envs)
    print(f"Running '{mod}' subcommand", end='')
    if envs:
        print(' with\n\t', ',\n\t'.join(f'{k}={shlex.quote(v)}' for k, v in envs.items()), end='')
    print()
    print('-' * 16, 'run', shlex.join(cmdline))
    try:
        subprocess.check_call(cmdline, env=new_env)
    except subprocess.CalledProcessError as e:
        print()
        raise Problem(str(e))
    print('-' * 16, 'finished', shlex.join(cmdline))


def install_dependencies():
    requirements_file = project_root('ci-requirements.txt')
    run_module('pip', 'install', '-r', requirements_file)


def extract_archive(archive, dest_dir):
    print(f'Extracting {archive} to {dest_dir}')

    def filter(tarinfo, path):
        assert '\\' not in tarinfo.path
        if '/' not in tarinfo.path:
            # toplevel, skip
            return None
        head, tail = tarinfo.path.split('/', 1)
        tarinfo.path = tail
        return tarfile.data_filter(tarinfo, path)

    shutil.unpack_archive(archive, dest_dir, None, filter=filter)


def perform_build(src_dir, dist_dir, make_sdist, make_wheel):
    args = [
        src_dir,
        '--sdist' if make_sdist else None,
        '--wheel' if make_wheel else None,
        '--outdir', dist_dir,
    ]
    args = [a for a in args if a is not None]
    env = dict(
        MONETDBE_INCLUDE_PATH=INC_DIR,
        MONETDBE_LIBRARY_PATH=LIB_DIR,
    )
    run_module('build', *args, **env)


def make_standalone(dist_dir, dyn_dir, manylinux, dest_dir):
    thin_wheels = glob.glob(os.path.join(dist_dir, '*.whl'))
    assert len(thin_wheels) == 1, f'Expected exactly one wheel in {dist_dir}, found {thin_wheels}'
    thin_wheel = thin_wheels[0]

    # If there are already wheels in dest_dir we cannot tell which one we created,
    # so we create it in an intermediate directory first
    intermediate_dir = os.path.join(SCRATCH_DIR, 'tmpwheels')

    # Leave the result in the intermediate directory
    run_module('repairwheel', thin_wheel, '-l', dyn_dir, '-o', intermediate_dir)

    # Find the name of the resulting fat wheel
    fat_wheels = glob.glob(os.path.join(intermediate_dir, '*.whl'))
    assert len(fat_wheels) == 1, f'Expected exactly one wheel in {intermediate_dir}, found {fat_wheels}'
    fat_wheel = fat_wheels[0]

    basename = os.path.basename(fat_wheel)
    if manylinux and 'manylinux' in basename:
        validate_manylinux(fat_wheel, manylinux)

    # Move it to dest_dir
    d = os.path.join(dest_dir, basename)
    print(f'Moving {fat_wheel} to {d}')
    os.rename(fat_wheel, d)


def validate_manylinux(wheel, allowed):
    # Parse required
    m = re.match(r'^(\d+)[._](\d+)$', allowed)
    if not m:
        raise Problem(f'MANYLINUX must be of the form 2_28 or 2.28, not {allowed_tuple}')
    allowed_major = int(m[1])
    allowed_minor = int(m[2])
    allowed_tuple = (allowed_major, allowed_minor)

    # Parse filename
    m = re.search(r'manylinux_(\d+)_(\d+)', os.path.basename(wheel))
    if not m:
        raise Problem(f'Cannot find tag manylinux_X_Y in file name {wheel}')
    actual_major = int(m[1])
    actual_minor = int(m[2])
    actual_tuple = (actual_major, actual_minor)

    if actual_tuple > allowed_tuple:
        raise Problem(f'Wheel manylinux tag of {wheel} is newer than {allowed}')


def main(args):
    global SCRATCH_DIR
    print('This is', shlex.join(sys.argv))
    # print(f'Args: {args}')
    print(f'Python is {sys.executable!r} ({sys.version})')
    if sys.prefix != sys.base_prefix:
        print(f'Running in venv:', sys.prefix)
    else:
        print(f'Not running in a venv')
    find_directories(args)

    # The actual work happens in main2().
    # Initialize or validate the working directory and invoke main2 with it.
    if args.scratch_dir:
        SCRATCH_DIR = args.scratch_dir
        # do not delete if inner because then we'd delete our venv
        initialize_scratch_dir(SCRATCH_DIR, delete=not args.inner)
        return main2(args)
    else:
        # Create a disposable scratch dir
        with tempfile.TemporaryDirectory(prefix='build-monetdbe-') as dir:
            SCRATCH_DIR = dir
            # do not delete if inner because then we'd delete our venv
            initialize_scratch_dir(SCRATCH_DIR, delete=not args.inner)
            return main2(args)


def main2(args):
    """A continuation of main(), running inside a 'with tempfile as' block"""
    if not args.inner:
        # create a venv and restart inside it, with --inner set
        return restart_in_venv()

    if args.install_dependencies:
        install_dependencies()

    try:
        os.mkdir(args.dest_dir)
    except FileExistsError:
        pass

    src_dir = args.source_dir
    if src_dir is None:
        src_dir = project_root()
    elif os.path.isdir(src_dir):
        pass
    else:
        src_tar = src_dir
        src_dir = os.path.join(SCRATCH_DIR, 'src')
        extract_archive(src_tar, src_dir)

    dist_dir = os.path.join(SCRATCH_DIR, 'dist')
    make_sdist = args.sdist
    make_wheel = args.wheel
    if not make_sdist and not make_wheel:
        make_sdist = True
        make_wheel = True
    perform_build(src_dir, dist_dir, make_sdist, make_wheel)

    if make_sdist:
        for s in glob.glob(os.path.join(dist_dir, '*.tar.gz')):
            d = os.path.join(args.dest_dir, os.path.basename(s))
            print(f'Moving {s} to {d}')
            os.rename(s, d)

    make_standalone(dist_dir, DYN_DIR, args.manylinux, args.dest_dir)


argparser = argparse.ArgumentParser(description=DESCR, epilog=EPILOG)
argparser.add_argument('-d', '--dest-dir', required=True,
                       help='Directory to leave wheel and sdist in')
argparser.add_argument('-s', '--source-dir',
                       help='Location of sources, either a dir or a .tar.gz')
argparser.add_argument('--sdist', action='store_true', help='Build source tar.gz file')
argparser.add_argument('--wheel', action='store_true', help='Build wheel')
argparser.add_argument('--inner', action='store_true',
                       help='Do not clear work dir and do not create a fresh virtual environment')
argparser.add_argument('--install-dependencies', action='store_true',
                       help='First install dependencies using pip')
argparser.add_argument('--inc-dir', help=f'directory containing {EXAMPLE_HEADER}. You can also set MONETDBE_INCLUDE_PATH.')
argparser.add_argument('--lib-dir', help=f'directory containing {EXAMPLE_LIB}. You can also set MONETDBE_LIBRARY_PATH.')
argparser.add_argument('--dyn-dir', help=f'directory containing {EXAMPLE_SO}. Usually derived from --lib-dir. You can also set MONETDBE_DYNAMIC_PATH.')
argparser.add_argument('--scratch-dir', help='directory in which to store temporary files. If unset, a temporary directory will be created and deleted afterwards ')
argparser.add_argument('--manylinux', help='Newest manylinux to accept, for example 2.28. Can also be written 2_28')

if __name__ == "__main__":
    args = argparser.parse_args()
    try:
        sys.exit(main(args) or 0)
    except Problem as e:
        print()
        print(f'Error: {e}')
        sys.exit(1)





