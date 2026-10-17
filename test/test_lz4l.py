import shutil

import pytest
from helpers import random_bytes, thumb_like

from leaninit import lz4l


def test_hand_made_block():
    # one token: 4 literals 'abcd', then a match at distance 4 of length 4
    block = bytes([0x40]) + b'abcd' + (4).to_bytes(2, 'little')
    frame = len(block).to_bytes(4, 'little') + block
    assert lz4l.decode_entry(frame) == (b'abcdabcd', len(frame))
    with pytest.raises(ValueError):
        lz4l.decode_entry(len(block).to_bytes(4, 'little') + bytes([0x40]) + b'abcd' + (0).to_bytes(2, 'little'))


@pytest.mark.skipif(shutil.which('lz4') is None, reason='lz4 executable not installed')
@pytest.mark.parametrize(
    'data',
    [thumb_like(40000, 1), random_bytes(3000, 2), b'', b'\x00' * 100000],
    ids=['thumb', 'random', 'empty', 'zeros'],
)
def test_round_trip_with_lz4_cli(data):
    entry = lz4l.encode_entry(data)
    back, used = lz4l.decode_entry(entry + b'tail')
    assert back == data
    assert used == len(entry)
