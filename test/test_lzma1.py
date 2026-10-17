import lzma

import pytest
from helpers import random_bytes, thumb_like

from leaninit import lzma1


def test_default_props_bytes():
    assert lzma1.Params().props() == bytes.fromhex('37 00 00 04 00')
    assert lzma1.Params().num_probs == 1984 + 0x300 * 4


@pytest.mark.parametrize(
    'p', [lzma1.Params(), lzma1.Params(lc=3, lp=0, pb=2, dict_size=1 << 20), lzma1.Params(lc=0, lp=4, pb=0)]
)
def test_props_round_trip(p):
    back = lzma1.Params.from_props(p.props())
    assert (back.lc, back.lp, back.pb, back.dict_size) == (p.lc, p.lp, p.pb, p.dict_size)


def test_params_validation():
    with pytest.raises(ValueError):
        lzma1.Params(lc=3, lp=2)
    with pytest.raises(ValueError):
        lzma1.Params(mf='bt5')
    with pytest.raises(ValueError):
        lzma1.Params(pb=5)
    with pytest.raises(ValueError):
        lzma1.Params.from_props(b'\xff\x00\x00\x04\x00')


@pytest.mark.parametrize(
    'data', [thumb_like(30000, 2), random_bytes(2000, 3), b'', b'a' * 1000], ids=['thumb', 'random', 'empty', 'runs']
)
def test_stdlib_decodes_what_cramjam_wrote(data):
    pytest.importorskip('cramjam')
    p = lzma1.Params()
    stream = lzma1.compress_raw(data, p, encoder='cramjam')
    assert lzma1.decompress_raw(stream, p, len(data)) == data


@pytest.mark.parametrize(
    'data', [thumb_like(30000, 2), random_bytes(2000, 3), b'', b'a' * 1000], ids=['thumb', 'random', 'empty', 'runs']
)
def test_encoders_agree(data):
    """Both backends are xz's encoder; the same parameters must give the same bytes."""
    pytest.importorskip('cramjam')
    p = lzma1.Params()
    assert lzma1.compress_raw(data, p, encoder='cramjam') == lzma1.compress_raw(data, p, encoder='stdlib')


def test_deterministic():
    data = thumb_like(10000, 5)
    assert lzma1.compress_raw(data) == lzma1.compress_raw(data)


def test_decompress_raw_is_strict():
    p = lzma1.Params()
    data = thumb_like(8000, 4)
    stream = lzma1.compress_raw(data, p)
    assert lzma1.decompress_raw(stream, p, len(data)) == data
    with pytest.raises((ValueError, lzma.LZMAError)):
        lzma1.decompress_raw(stream[:-1], p, len(data))  # marker cut
    with pytest.raises((ValueError, lzma.LZMAError)):
        lzma1.decompress_raw(stream[: len(stream) // 2], p, len(data))  # body cut
    with pytest.raises(ValueError):
        lzma1.decompress_raw(stream + b'\x00', p, len(data))  # trailing byte
    with pytest.raises(ValueError):
        lzma1.decompress_raw(stream, p, len(data) + 1)
    with pytest.raises(ValueError):
        lzma1.decompress_raw(stream, p, len(data) - 1)


def test_backend_info_names_a_backend():
    info = lzma1.backend_info()
    assert 'cramjam' in info or 'stdlib' in info
    assert 'stdlib' in lzma1.backend_info('stdlib')
    with pytest.raises(ValueError):
        lzma1.resolve_encoder('xz')
