#!/usr/bin/env python3

from pathlib import Path
import subprocess
import sys

import hashlib

hasher = hashlib.sha512()


def add(text):
    assert isinstance(text, str)
    # print(f'hashing {text!r}', file=sys.stderr)
    hasher.update(bytes(text, 'utf-8'))


for arg in sys.argv[1:]:
    add(f'arg {arg!r}')

ls_files = subprocess.check_output(['git', 'ls-files'], encoding='ascii').splitlines()

github_workflows_path = Path('.github', 'workflows')


def is_to_be_hashed(path: Path, content: bytes) -> bool:
    # Exclude the github workflows, they don't affect the result.
    # Except for the workflow that invokes us
    if path.parent == github_workflows_path:
        return False
    return True


for name in sorted(ls_files):
    path = Path(name)
    canonical = '/'.join(path.parts)
    with open(name, 'rb') as f:
        content = f.read()
    if is_to_be_hashed(path, content):
        subhasher = hashlib.sha512()
        subhasher.update(content)
        digest = subhasher.hexdigest()
        add(f'file {canonical}={digest}')
    else:
        # print(f'- skip {name}', file=sys.stderr)
        pass

digest = hasher.hexdigest()
hash = digest[:32]
print(f'hash={hash}')