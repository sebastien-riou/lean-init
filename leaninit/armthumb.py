"""ARM-Thumb branch-call-jump (BCJ) filter, as implemented by xz (``simple/armthumb.c``).

Thumb-2 ``BL`` instructions encode a relative target split over two 16-bit halves
(``0xF000 | hi11`` then ``0xF800 | lo11``). Rewriting the relative target as an absolute
one makes repeated calls to the same function identical byte sequences, which an LZ-class
compressor then matches. The transform is reversible given the position of the data.

Both directions operate on a copy and never change the length. ``now_pos`` is the
position of ``buf[0]`` in the filtered stream; it is 0 for a stream that starts at the
section's first byte, which is how leaninit uses it.
"""


def _transform(buf: bytes, now_pos: int, *, encoding: bool) -> bytes:
    b = bytearray(buf)
    i = 0
    n = len(b)
    while i + 4 <= n:
        if (b[i + 1] & 0xF8) == 0xF0 and (b[i + 3] & 0xF8) == 0xF8:
            src = ((b[i + 1] & 7) << 19) | (b[i] << 11) | ((b[i + 3] & 7) << 8) | b[i + 2]
            src <<= 1
            if encoding:
                dest = (src + (now_pos + i + 4)) & 0xFFFFFFFF
            else:
                dest = (src - (now_pos + i + 4)) & 0xFFFFFFFF
            dest >>= 1
            b[i + 1] = 0xF0 | ((dest >> 19) & 7)
            b[i] = (dest >> 11) & 0xFF
            b[i + 3] = 0xF8 | ((dest >> 8) & 7)
            b[i + 2] = dest & 0xFF
            i += 2
        i += 2
    return bytes(b)


def encode(buf: bytes, now_pos: int = 0) -> bytes:
    """Relative ``BL`` targets become absolute (what the compressor sees)."""
    return _transform(buf, now_pos, encoding=True)


def decode(buf: bytes, now_pos: int = 0) -> bytes:
    """Absolute ``BL`` targets become relative again (what the decompressor must do)."""
    return _transform(buf, now_pos, encoding=False)
