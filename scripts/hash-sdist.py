#!/usr/bin/env python3

import hashlib
import sys
import tarfile

algo = 'sha256'

member_hashes = []

with tarfile.open(sys.argv[1], mode='r') as tar:
    for member in tar:
        name = member.name
        f = tar.extractfile(member)
        if f is None:
            continue
        content = f.read()
        hasher = hashlib.new(algo)
        hasher.update(content)
        bindigest = hasher.digest()
        member_hashes.append((name, bindigest))

hasher = hashlib.new(algo)
hasher.update(b'tralala')

# Make sure to sort the members
for name, file_digest in sorted(member_hashes):
    hasher.update(bytes(name, 'utf-8'))
    hasher.update(file_digest)

hex = hasher.hexdigest()
print(f'sdist-hash={hex}')