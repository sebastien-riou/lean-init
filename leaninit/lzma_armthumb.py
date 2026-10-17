"""The ``lzma-armthumb`` codec: ARM-Thumb BCJ filter, then raw LZMA1.

Entry payload layout (16-byte header, then the stream):

    u32 LE  compressed_len      length of the raw LZMA1 stream that follows
    u32 LE  uncompressed_len    exact size of the decoded data
    u8[5]   props               LZMA properties: lc/lp/pb byte, dictionary size LE
    u8[3]   zero                reserved, keeps the stream 4-byte aligned
    u8[]    stream

Raw LZMA1 has no length field of its own, so ``compressed_len`` is what lets the walker
in ``leaninit.h`` find the next entry; ``uncompressed_len`` gives the decoder an exact
output size; the props let it refuse a build it was not compiled for.
"""

import struct

from leaninit import armthumb, lzma1

HEADER = struct.Struct('<II5s3x')
HEADER_SIZE = HEADER.size
assert HEADER_SIZE == 16


def encode_entry(data: bytes, params: lzma1.Params | None = None, encoder: str = 'auto') -> bytes:
    """Filter, compress and frame ``data``; verified by decoding it again before returning."""
    params = params or lzma1.Params()
    stream = lzma1.compress_raw(armthumb.encode(data), params, encoder)
    entry = HEADER.pack(len(stream), len(data), params.props()) + stream
    back, used = decode_entry(entry)
    if back != data or used != len(entry):
        raise RuntimeError('lzma-armthumb self-check failed: the entry does not decode back to its input')
    return entry


def entry_length(buf: bytes, off: int = 0) -> int:
    """Total length of the entry starting at ``off``, header included."""
    if off + HEADER_SIZE > len(buf):
        raise ValueError('truncated lzma-armthumb entry header')
    comp_len, _, _ = HEADER.unpack_from(buf, off)
    return HEADER_SIZE + comp_len


def decode_entry(buf: bytes, off: int = 0) -> tuple[bytes, int]:
    """Decode the entry at ``off`` with the standard library. Returns (data, bytes consumed)."""
    comp_len, uncomp_len, props = HEADER.unpack_from(buf, off)
    if any(buf[off + 13 : off + 16]):
        raise ValueError('reserved bytes of the lzma-armthumb header are not zero')
    start = off + HEADER_SIZE
    end = start + comp_len
    if end > len(buf):
        raise ValueError('truncated lzma-armthumb stream')
    params = lzma1.Params.from_props(props)
    filtered = lzma1.decompress_raw(buf[start:end], params, uncomp_len)
    return armthumb.decode(filtered), end - off
