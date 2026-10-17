import struct

import pytest
from helpers import random_bytes, thumb_like

from leaninit import lzma1, lzma_armthumb


@pytest.mark.parametrize(
    'data',
    [thumb_like(40000, 1), random_bytes(3000, 2), b'', b'\x00' * 100000],
    ids=['thumb', 'random', 'empty', 'zeros'],
)
def test_round_trip(data):
    entry = lzma_armthumb.encode_entry(data)
    comp_len, uncomp_len, props = struct.unpack_from('<II5s', entry)
    assert entry[13:16] == b'\x00\x00\x00'
    assert uncomp_len == len(data)
    assert comp_len == len(entry) - 16
    assert props == lzma1.Params().props()
    assert lzma_armthumb.entry_length(entry) == len(entry)
    back, used = lzma_armthumb.decode_entry(b'xx' + entry + b'tail', 2)
    assert back == data
    assert used == len(entry)


def test_deterministic():
    data = thumb_like(10000, 3)
    assert lzma_armthumb.encode_entry(data) == lzma_armthumb.encode_entry(data)


def test_custom_params_are_recorded():
    p = lzma1.Params(lc=0, lp=2, pb=2, dict_size=1 << 16)
    entry = lzma_armthumb.encode_entry(thumb_like(5000, 4), p)
    assert entry[8:13] == p.props()
    assert lzma_armthumb.decode_entry(entry)[0] == thumb_like(5000, 4)


def test_rejects_damaged_entries():
    data = thumb_like(20000, 5)
    entry = bytearray(lzma_armthumb.encode_entry(data))
    bad = bytes(entry[:14]) + b'\x01' + bytes(entry[15:])
    with pytest.raises(ValueError):
        lzma_armthumb.decode_entry(bad)
    with pytest.raises(ValueError):
        lzma_armthumb.decode_entry(bytes(entry[:-5]))  # truncated
    with pytest.raises(ValueError):
        lzma_armthumb.entry_length(bytes(entry[:10]))
    flipped = bytearray(entry)
    flipped[len(flipped) // 2] ^= 0xFF
    try:
        back, _ = lzma_armthumb.decode_entry(bytes(flipped))
    except Exception:
        return
    assert back != data
