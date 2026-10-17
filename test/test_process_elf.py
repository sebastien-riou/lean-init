"""process_elf() end to end on a small 32-bit ELF linked with the host binutils.

Needs ``as --32`` and ``ld -m elf_i386`` (any x86-64 Linux binutils); skipped otherwise.
"""

import shutil
import subprocess

import pytest
from helpers import random_bytes, thumb_like

from leaninit import table
from leaninit.cli import process_elf

LD_SCRIPT = """
MEMORY {{
  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 128K
  RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 256K
}}
SECTIONS {{
  .text   : {{ *(.text*) }} > FLASH
  .version : ALIGN(8) {{ __version = .; LONG(0x11223344) LONG(0) }} > FLASH
  .data   : {{ *(.data*) }} > RAM
  .rodata : {{ *(.rodata*) }} > RAM
  .gap    : ALIGN(64) {{ *(.gap*) }} > RAM   /* a hole before it: must not merge with .rodata */
  .leaninit : ALIGN(4) {{
    __leaninit_table = .;
    {names}
    BYTE(0)
    LONG(LENGTH(FLASH))
    LONG(16) LONG(16)
    LONG(0xaaaaaaaa) LONG(0xbbbbbbbb) LONG(0xcccccccc) LONG(__version - ORIGIN(FLASH))
    . = ORIGIN(FLASH) + LENGTH(FLASH);
  }} > FLASH
}}
"""


def asciz(name):
    return ' '.join(f'BYTE({b})' for b in name.encode() + b'\x00')


@pytest.fixture(scope='module')
def host_elf(tmp_path_factory):
    for tool in ('as', 'ld', 'objcopy', 'readelf', 'objdump'):
        if shutil.which(tool) is None:
            pytest.skip(f'host {tool} not available')
    d = tmp_path_factory.mktemp('elf')
    data = thumb_like(30001, 1)
    rodata = thumb_like(7003, 2)
    gap = random_bytes(513, 3)
    for name, blob in (('data', data), ('rodata', rodata), ('gap', gap)):
        (d / f'{name}.bin').write_bytes(blob)
    (d / 'src.s').write_text(
        '.section .text\nnop\n'
        '.section .data\n.incbin "data.bin"\n'
        '.section .rodata\n.incbin "rodata.bin"\n'
        '.section .gap,"aw"\n.incbin "gap.bin"\n'
    )
    names = '\n    '.join(asciz(n) for n in ('.data', '.rodata', '.gap', '.absent?'))
    (d / 'link.ld').write_text(LD_SCRIPT.format(names=names))
    try:
        subprocess.run(['as', '--32', '-o', 'src.o', 'src.s'], cwd=d, check=True, capture_output=True)
        subprocess.run(
            ['ld', '-m', 'elf_i386', '-T', 'link.ld', '-o', 'in.elf', 'src.o'], cwd=d, check=True, capture_output=True
        )
    except subprocess.CalledProcessError as e:
        pytest.skip(f'host binutils cannot build a 32-bit ELF: {e.stderr.decode()}')
    return d, {'.data': (0x20000000, data), '.rodata': (0x20000000 + len(data), rodata), 'gap': gap}


def dump(elf, section, out):
    subprocess.run(['objcopy', '-O', 'binary', '--only-section=' + section, elf, out], check=True)
    return open(out, 'rb').read()


def codecs():
    out = ['lzma-armthumb']
    if shutil.which('lz4'):
        out.append('lz4l')
    return out


@pytest.mark.parametrize('codec', codecs())
def test_process_elf_round_trip(host_elf, tmp_path, codec):
    d, expect = host_elf
    source = random_bytes(8192, 7)
    (tmp_path / 'pad.bin').write_bytes(source)
    out_elf = str(tmp_path / 'out.elf')
    layout = process_elf(
        str(d / 'in.elf'), binutils_prefix='', out_elf=out_elf, codec=codec, pad_to=8192, pad_source=source
    )
    tbl = dump(out_elf, '.leaninit', str(tmp_path / 'tbl.bin'))
    assert tbl == layout.data
    subprocess.run(['objcopy', '-O', 'binary', out_elf, str(tmp_path / 'image.bin')], check=True)
    image = (tmp_path / 'image.bin').read_bytes()
    assert len(image) % 8192 == 0
    assert image.endswith(layout.data)
    assert image[-16:] == tbl[-16:]
    # footer: our linker script put __version - ORIGIN(FLASH) in its last word
    version_off = int.from_bytes(image[-4:], 'little')
    assert image[version_off : version_off + 4] == bytes.fromhex('44332211')

    parsed = table.parse_table(
        tbl, pointer_size=4, leaninit_vma=0x08000000 + len(image) - len(tbl), codec=table.make_codec(codec)
    )
    data_vma, data = expect['.data']
    _, rodata = expect['.rodata']
    entries = sorted(parsed.entries)  # merged sections are appended last; order is irrelevant to the walker
    assert len(entries) == 2
    assert entries[0] == (data_vma, data + rodata)  # .data and .rodata were contiguous: merged
    assert entries[1][1] == expect['gap']
    assert entries[1][0] % 64 == 0
    assert entries[1][0] > data_vma + len(data) + len(rodata)
    pad = tbl[parsed.tail_offset : -16]
    assert pad == source[: len(pad)]
    # compressed sections are gone from the output ELF
    hdr = subprocess.run(['readelf', '-S', '-W', out_elf], check=True, capture_output=True, text=True).stdout
    assert '.data' not in hdr and '.rodata' not in hdr and '.gap' not in hdr
    assert '.leaninit' in hdr and '.version' in hdr
