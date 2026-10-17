import shutil

import pytest
from helpers import random_bytes, thumb_like

from leaninit import padding, table

VMA = 0x08000388  # not page aligned, like a real image
PTR = 4
FOOTER = bytes(range(16))


def directive(*, footer=True):
    return table.Directive([], 512 * 1024, 16 if footer else 0, 16 if footer else 0, FOOTER if footer else None)


def sections(codec):
    out = [
        table.Section('.a', 0x20000000, 0x20000000, 30000, thumb_like(30000, 1)),
        table.Section('.b', 0x20010000, 0x20010000, 500, random_bytes(500, 2)),
    ]
    for s in out:
        s.payload = codec.encode(s.data)
    return out


def codecs():
    out = [table.make_codec('lzma-armthumb')]
    if shutil.which('lz4'):
        out.append(table.make_codec('lz4l'))
    return out


@pytest.mark.parametrize('codec', codecs(), ids=lambda c: c.name)
def test_table_without_padding(codec):
    secs = sections(codec)
    layout = table.build_table(secs, pointer_size=PTR, leaninit_vma=VMA, directive=directive())
    data = layout.data
    assert int.from_bytes(data[:PTR], 'little') == len(data)
    assert data[-16:] == FOOTER
    assert (VMA + len(data) - 16) % 16 == 0
    assert layout.pad_size < 16
    parsed = table.parse_table(data, pointer_size=PTR, leaninit_vma=VMA, codec=codec)
    assert parsed.entries == [(s.vma, s.data) for s in secs]
    assert data[parsed.tail_offset : parsed.tail_offset + layout.pad_size] == bytes(layout.pad_size)
    assert layout.image_end == VMA + len(data)


@pytest.mark.parametrize('codec', codecs(), ids=lambda c: c.name)
def test_table_padded_to_page(codec):
    secs = sections(codec)
    source = random_bytes(8192, 9)
    layout = table.build_table(
        secs, pointer_size=PTR, leaninit_vma=VMA, directive=directive(), pad_to=8192, pad_source=source
    )
    data = layout.data
    assert (VMA + len(data)) % 8192 == 0
    assert layout.image_end == VMA + len(data)
    assert data[-16:] == FOOTER
    parsed = table.parse_table(data, pointer_size=PTR, leaninit_vma=VMA, codec=codec)
    assert parsed.entries == [(s.vma, s.data) for s in secs]
    pad = data[parsed.tail_offset : -16]
    assert len(pad) == layout.pad_size
    assert pad == source[: len(pad)]
    assert len(data) <= len(data) + 8191


def test_pad_without_footer():
    codec = table.make_codec('lzma-armthumb')
    secs = sections(codec)
    source = random_bytes(8192, 9)
    layout = table.build_table(
        secs, pointer_size=PTR, leaninit_vma=VMA, directive=directive(footer=False), pad_to=8192, pad_source=source
    )
    assert (VMA + len(layout.data)) % 8192 == 0
    assert layout.footer_offset is None
    assert layout.data[-layout.pad_size :] == source[: layout.pad_size]


def test_pad_errors():
    codec = table.make_codec('lzma-armthumb')
    secs = sections(codec)
    with pytest.raises(ValueError):
        table.build_table(
            secs, pointer_size=PTR, leaninit_vma=VMA, directive=directive(), pad_to=8192, pad_source=b'x' * 10
        )
    with pytest.raises(ValueError):
        table.build_table(secs, pointer_size=PTR, leaninit_vma=VMA, directive=directive(), pad_to=8192)
    with pytest.raises(ValueError):
        table.build_table(
            secs, pointer_size=PTR, leaninit_vma=VMA, directive=directive(), pad_to=1000, pad_source=bytes(1000)
        )


def test_pad_from_content_hash_is_deterministic_and_marked_weaker():
    codec = table.make_codec('lzma-armthumb')
    a = table.build_table(
        sections(codec), pointer_size=PTR, leaninit_vma=VMA, directive=directive(), pad_to=8192, pad_from_content=True
    )
    b = table.build_table(
        sections(codec), pointer_size=PTR, leaninit_vma=VMA, directive=directive(), pad_to=8192, pad_from_content=True
    )
    assert a.data == b.data
    assert 'recompute' in padding.__doc__


def test_parse_rejects_wrong_size_word():
    codec = table.make_codec('lzma-armthumb')
    layout = table.build_table(sections(codec), pointer_size=PTR, leaninit_vma=VMA, directive=directive())
    with pytest.raises(ValueError):
        table.parse_table(layout.data + b'\x00', pointer_size=PTR, leaninit_vma=VMA, codec=codec)
