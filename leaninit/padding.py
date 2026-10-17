"""Bytes used to pad an image up to a fixed boundary.

The pad sits inside the signed image and is hashed by any attestation that covers the
image, so what it contains has a security meaning. Bytes taken from a committed random
file cannot be derived from the rest of the image, so anything that wants to reproduce
the image has to store them: that is the cost a memory-hard attestation argument wants
every byte to carry. Bytes derived from the image's own content hash are reproducible
and incompressible too, but a program that already holds the content can recompute them
for free; that variant only fixes the geometry of the image, and is offered as the
explicitly weaker option.
"""

import hashlib

CONTENT_SEED_DOMAIN = b'leaninit-pad-v1\0'


def pad_bytes(n: int, *, source: bytes | None = None, seed: bytes | None = None) -> bytes:
    if n < 0:
        raise ValueError('negative pad length')
    if (source is None) == (seed is None):
        raise ValueError('exactly one of source and seed must be given')
    if source is not None:
        if len(source) < n:
            raise ValueError(f'pad source holds {len(source)} bytes, {n} are needed')
        return bytes(source[:n])
    return hashlib.shake_256(CONTENT_SEED_DOMAIN + seed).digest(n) if n else b''
