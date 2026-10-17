"""The ``.leaninit`` table: what the linker leaves there, what the tool writes back.

Input (written by the linker script):

    ASCIZ names of the sections to compress, ``?`` suffix marking optional ones, then an
    empty name; ptr region size (reporting only); ptr footer size; if non-zero, ptr footer
    alignment and the footer bytes.

Output (what ``leaninit_init`` walks, see ``include/leaninit.h``):

    ptr     total size of the table, footer and padding included (``fw_size()`` style users
            read this word to know where the image ends)
    entry*  ptr destination VMA, then the codec's payload
    ptr     terminator: the VMA of the ``.leaninit`` section itself
    pad     optional, only with ``pad_to``; the decoder never reads it
    footer  optional, aligned as the linker script asked, always last

``ptr`` is the target pointer width, little endian, as the header reads it byte by byte.
Every multi-byte field inside a codec payload is 32-bit little endian regardless of the
target.
"""

import copy
import io
import logging
from dataclasses import dataclass, field

from leaninit import lz4l, lzma1, lzma_armthumb, padding
from leaninit.elf import SectionNameNotFoundError

CODECS = ('lz4l', 'lzma-armthumb')


@dataclass
class Directive:
    """What the linker script put in ``.leaninit``."""

    sections_start_addr: list[int]
    region_size: int
    footer_size: int
    footer_align: int
    footer_data: bytes | None


@dataclass
class Section:
    name: str
    lma: int
    vma: int
    size: int
    data: bytes
    merged: bool = False
    payload: bytes = field(default=b'', repr=False)


@dataclass
class Codec:
    name: str
    encode: callable
    decode: callable
    describe: str


def make_codec(name: str, *, lzma_params: lzma1.Params | None = None, lzma_encoder: str = 'auto') -> Codec:
    if name == 'lz4l':
        return Codec('lz4l', lz4l.encode_entry, lz4l.decode_entry, 'lz4 -9 -l (system lz4 executable)')
    if name == 'lzma-armthumb':
        p = lzma_params or lzma1.Params()
        return Codec(
            'lzma-armthumb',
            lambda data: lzma_armthumb.encode_entry(data, p, lzma_encoder),
            lzma_armthumb.decode_entry,
            f'ARM-Thumb BCJ + raw LZMA1 {p}, encoder {lzma1.backend_info(lzma_encoder)}',
        )
    raise ValueError(f'unknown codec {name!r}, expected one of {CODECS}')


def read_directive(elf, leaninit_section) -> Directive:
    pointer_size = elf.addr_width // 8
    stream = io.BytesIO(elf.get_section_data(leaninit_section['name']))

    def read_ptr():
        out = int.from_bytes(stream.read(pointer_size), byteorder=elf.byteorder)
        logging.debug(f'read_ptr: {out}')
        return out

    def read_str():
        out = bytearray()
        while True:
            c = stream.read(1)
            if len(c) == 0:
                raise RuntimeError('.leaninit ends inside the section name list')
            if c[0] == 0:
                break
            out += c
        out = out.decode()
        logging.debug(f'read_str: {out}')
        return out

    sections_start_addr = []
    while True:
        name = read_str()
        if len(name) == 0:
            break
        is_optional = name.endswith('?')
        if is_optional:
            name = name[:-1]
        try:
            section = elf.get_section_by_name(name)
            sections_start_addr.append(section['lma'])
        except SectionNameNotFoundError:
            if is_optional:
                logging.debug(f'Optional section "{name}" not found')  # assume the section has been removed
            else:
                raise RuntimeError(f'Mandatory section "{name}" not found') from None
    region_size = read_ptr()
    footer_size = read_ptr()
    footer_align = 0
    footer_data = None
    if footer_size != 0:
        footer_align = read_ptr()
        footer_data = stream.read(footer_size)
        if len(footer_data) != footer_size:
            raise RuntimeError('.leaninit ends inside the footer')
        if footer_align == 0:
            footer_align = 1
    return Directive(sections_start_addr, region_size, footer_size, footer_align, footer_data)


def collect_sections(elf, sections_start_addr: list[int]) -> tuple[list[Section], list[str]]:
    """Read the sections at those LMAs and merge the ones that are contiguous in load memory.

    Returns the sections to store (merged ones carry a synthetic name) and the names of the
    ELF sections that merged ones replace. Nothing is deleted from ``elf`` here.
    """
    starts = list(sections_start_addr)
    ends = []
    sections = []
    for lma in starts:
        s = elf.get_section_by_lma(lma)
        data = elf.get_section_data(s['name'])
        ends.append(lma + s['size'] - 1)
        sections.append(Section(s['name'], lma, s['vma'], len(data), data))

    merged = True
    merge_cnt = 0
    to_delete = []
    while merged:
        merged = False
        for last in ends:
            if last + 1 in starts:
                low_i = ends.index(last)
                high_i = starts.index(last + 1)
                low = copy.deepcopy(sections[low_i])
                high = copy.deepcopy(sections[high_i])
                logging.debug(f'Merging {low.name} and {high.name}')
                del starts[low_i], ends[low_i], sections[low_i]
                high_i = starts.index(last + 1)  # refresh index
                del starts[high_i], ends[high_i], sections[high_i]
                to_delete += [high.name, low.name]
                merge_cnt += 1
                data = low.data + high.data
                starts.append(low.lma)
                ends.append(high.lma + high.size - 1)
                sections.append(Section(f'.leaninit_merge{merge_cnt}', low.lma, low.vma, len(data), data, merged=True))
                merged = True
                break
    return sections, to_delete


def _round_up(x: int, n: int) -> int:
    return -(-x // n) * n


@dataclass
class Layout:
    data: bytes
    pad_size: int
    footer_offset: int | None
    image_end: int  # absolute address one past the last byte


def build_table(
    sections: list[Section],
    *,
    pointer_size: int,
    leaninit_vma: int,
    directive: Directive,
    pad_to: int = 0,
    pad_source: bytes | None = None,
    pad_from_content: bool = False,
) -> Layout:
    """Assemble the output table from sections whose ``payload`` is already encoded."""
    out = bytearray(pointer_size)  # total size, patched at the end

    def write_ptr(addr):
        out.extend(addr.to_bytes(pointer_size, byteorder='little'))

    for s in sections:
        if not s.payload:
            raise ValueError(f'section {s.name} has no encoded payload')
        write_ptr(s.vma)
        out.extend(s.payload)
    write_ptr(leaninit_vma)

    footer_size = directive.footer_size
    footer_align = directive.footer_align if footer_size else 1
    end = leaninit_vma + len(out)
    if pad_to:
        if pad_to % footer_align:
            raise ValueError(f'pad_to ({pad_to}) must be a multiple of the footer alignment ({footer_align})')
        if footer_size % footer_align:
            raise ValueError(
                f'a footer of {footer_size} bytes cannot end on a {pad_to}-byte boundary and stay {footer_align}-aligned'
            )
        image_end = _round_up(end + footer_size, pad_to)
        footer_start = image_end - footer_size
    else:
        footer_start = _round_up(end, footer_align) if footer_size else end
        image_end = footer_start + footer_size
    pad_size = footer_start - end
    if pad_size:
        if pad_from_content:
            out.extend(padding.pad_bytes(pad_size, seed=bytes(out)))
        elif pad_source is not None:
            out.extend(padding.pad_bytes(pad_size, source=pad_source))
        elif pad_to:
            raise ValueError('pad_to needs pad_source (or pad_from_content)')
        else:
            out.extend(bytes(pad_size))  # footer alignment filler only, as before padding existed
    footer_offset = None
    if footer_size:
        footer_offset = len(out)
        out.extend(directive.footer_data)
    assert leaninit_vma + len(out) == image_end
    out[0:pointer_size] = len(out).to_bytes(pointer_size, byteorder='little')
    return Layout(bytes(out), pad_size, footer_offset, image_end)


@dataclass
class ParsedTable:
    total_size: int
    entries: list[tuple[int, bytes]]  # (destination VMA, decoded data)
    tail_offset: int  # first byte after the terminator: padding, then footer


def parse_table(data: bytes, *, pointer_size: int, leaninit_vma: int, codec: Codec) -> ParsedTable:
    """Walk an output table the way ``leaninit_init`` does, decoding every entry on the host."""
    total = int.from_bytes(data[0:pointer_size], 'little')
    if total != len(data):
        raise ValueError(f'table size word says {total}, section holds {len(data)} bytes')
    pos = pointer_size
    entries = []
    while True:
        dst = int.from_bytes(data[pos : pos + pointer_size], 'little')
        pos += pointer_size
        if dst == leaninit_vma:
            break
        decoded, used = codec.decode(data, pos)
        pos += used
        entries.append((dst, decoded))
    return ParsedTable(total, entries, pos)
