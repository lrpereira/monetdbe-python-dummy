#!/usr/bin/env python3

import argparse, os, runpy

argparser = argparse.ArgumentParser()
argparser.add_argument('version', nargs='?')
args = argparser.parse_args()

if args.version:
    version = args.version
else:
    version_module_path = os.path.join('monetdbe', 'version.py')
    version_module = runpy.run_path(version_module_path)
    version_tuple = version_module['version_tuple']
    version = f'11.{version_tuple[0]}.{version_tuple[1]}'

print(f'monetdb-version={version}')