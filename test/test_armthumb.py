import lzma

import pytest
from helpers import thumb_like

from leaninit import armthumb


@pytest.mark.parametrize('seed', range(4))
def test_round_trip(seed):
    data = thumb_like(5000 + 7 * seed, seed)
    enc = armthumb.encode(data)
    assert enc != data
    assert len(enc) == len(data)
    assert armthumb.decode(enc) == data


def test_matches_liblzma_filter():
    """The Python filter must be bit-exact with xz's, since the C inverse is written against xz."""
    data = thumb_like(20000, 1)
    lzma1 = {'id': lzma.FILTER_LZMA1, 'dict_size': 1 << 16, 'lc': 1, 'lp': 1, 'pb': 1}
    stream = lzma.compress(data, format=lzma.FORMAT_RAW, filters=[{'id': lzma.FILTER_ARMTHUMB}, lzma1])
    filtered = lzma.decompress(stream, format=lzma.FORMAT_RAW, filters=[lzma1])
    assert filtered == armthumb.encode(data)


def test_now_pos_matches_offset_in_stream():
    data = thumb_like(3000, 2)
    prefix = bytes(64)  # zeros never form a BL pattern
    assert armthumb.encode(prefix + data)[64:] == armthumb.encode(data, now_pos=64)
    assert armthumb.decode(armthumb.encode(data, now_pos=64), now_pos=64) == data


def test_short_and_odd_inputs():
    for data in (b'', b'\xf0', b'\x00\xf0\x00\xf8', b'\x00\xf0\x00'):
        assert armthumb.decode(armthumb.encode(data)) == data
    assert armthumb.encode(b'\x00\xf0\x00') == b'\x00\xf0\x00'  # fewer than 4 bytes: untouched
