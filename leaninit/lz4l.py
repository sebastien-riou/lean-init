"""LZ4 "legacy" frames (``lz4 -l``) as leaninit stores them: one block, no frame magic."""

import os
import shutil
import subprocess
import tempfile

LZ4_LEGACY_MAGIC = b'\x02\x21\x4c\x18'


def compress(data: bytes, *, lz4_path: str | None = None) -> bytes:
    """Run the ``lz4`` CLI at level 9 in legacy mode and return the whole frame, magic included."""
    lz4 = lz4_path or shutil.which('lz4')
    if lz4 is None:
        raise RuntimeError('lz4 executable not found in PATH (install the lz4 package or use --codec lzma-armthumb)')
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, 'in.bin')
        dst = os.path.join(tmp, 'out.lz4')
        with open(src, 'wb') as f:
            f.write(data)
        subprocess.run([lz4, '-9', '-l', '-f', src, dst], check=True, capture_output=True)  # noqa: S603
        with open(dst, 'rb') as f:
            frame = f.read()
    if frame[:4] != LZ4_LEGACY_MAGIC:
        raise RuntimeError('lz4 did not produce a legacy frame')
    return frame


def encode_entry(data: bytes) -> bytes:
    """The bytes leaninit stores for ``data``: the legacy frame without its magic.

    ``lz4 -l`` writes no block at all for empty input; the decoder needs a zero block size to
    stop on, so one is appended in that case.
    """
    body = compress(data)[4:]
    return body if body else bytes(4)


def decode_entry(buf: bytes, off: int = 0) -> tuple[bytes, int]:
    """Decode a magic-less legacy frame at ``off``, mirroring ``leaninit_decompress`` in leaninit.h.

    Returns (data, bytes consumed). Like the C decoder it stops after the first block
    (``lz4 -l`` writes one block per 8 MiB of input, and leaninit never stores more).
    """
    pos = off
    block_size = int.from_bytes(buf[pos : pos + 4], 'little')
    pos += 4
    out = bytearray()
    if block_size == 0:
        return bytes(out), pos - off
    end = pos + block_size
    if end > len(buf):
        raise ValueError('truncated lz4 block')
    while pos < end:
        token = buf[pos]
        pos += 1
        literals = token >> 4
        if literals == 15:
            while True:
                c = buf[pos]
                pos += 1
                literals += c
                if c != 255:
                    break
        out += buf[pos : pos + literals]
        pos += literals
        if pos == end:
            break
        delta = int.from_bytes(buf[pos : pos + 2], 'little')
        pos += 2
        if delta == 0:
            raise ValueError('invalid lz4 match offset 0')
        match = 4 + (token & 0x0F)
        if match == 4 + 0x0F:
            while True:
                c = buf[pos]
                pos += 1
                match += c
                if c != 255:
                    break
        ref = len(out) - delta
        if ref < 0:
            raise ValueError('lz4 match offset before the start of the output')
        for _ in range(match):
            out.append(out[ref])
            ref += 1
    if pos != end:
        raise ValueError('lz4 block overran its declared size')
    return bytes(out), pos - off
