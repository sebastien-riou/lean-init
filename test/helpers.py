"""Shared test inputs."""

import random


def thumb_like(n: int, seed: int = 0) -> bytes:
    """Bytes that look enough like Thumb-2 code for the ARM-Thumb filter and LZMA to bite.

    A small vocabulary of 16-bit words (so matches exist), random noise, and about one BL
    instruction in ten: ``0xF000|hi11`` then ``0xF800|lo11`` with a signed halfword offset.
    """
    rnd = random.Random(seed)
    words = [rnd.getrandbits(16) for _ in range(64)]
    out = bytearray()
    while len(out) < n:
        r = rnd.random()
        if r < 0.1:
            off = rnd.randrange(-20000, 20000) & 0x3FFFFF
            out += (0xF000 | ((off >> 11) & 0x7FF)).to_bytes(2, 'little')
            out += (0xF800 | (off & 0x7FF)).to_bytes(2, 'little')
        elif r < 0.6:
            out += words[rnd.randrange(64)].to_bytes(2, 'little')
        else:
            out += rnd.getrandbits(16).to_bytes(2, 'little')
    return bytes(out[:n])


def random_bytes(n: int, seed: int = 0) -> bytes:
    return random.Random(seed).randbytes(n)
