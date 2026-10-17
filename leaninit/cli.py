import argparse
import logging
import os
import sys

import humanfriendly

from leaninit import lzma1, table
from leaninit.elf import Elf


def format_size(size):
    return humanfriendly.format_size(size, binary=True)


def process_elf(
    org_elf_file,
    *,
    binutils_prefix,
    out_elf=None,
    codec='lz4l',
    lzma_params=None,
    lzma_encoder='auto',
    pad_to=0,
    pad_source=None,
    pad_from_content=False,
):
    """Compress the sections named in ``.leaninit`` and write the table back into the ELF.

    ``pad_to`` pads the image so that it ends on a multiple of that many bytes; the pad
    bytes come from ``pad_source`` (a bytes object, normally the content of a committed
    random file) or, with ``pad_from_content``, from a hash of the table. See
    ``leaninit/padding.py`` for why the file is the default.
    """
    if pad_to and not pad_from_content and pad_source is None:
        raise ValueError('pad_to needs pad_source (or pad_from_content)')
    the_codec = table.make_codec(codec, lzma_params=lzma_params, lzma_encoder=lzma_encoder)

    elf = Elf(org_elf_file, binutils_prefix=binutils_prefix)
    pointer_size = elf.addr_width // 8
    leaninit_section = elf.get_section_by_name('.leaninit')
    if (leaninit_section['lma'] % pointer_size) > 0:
        raise RuntimeError(f"{leaninit_section['name']} is not aligned to pointer size ({pointer_size})")
    directive = table.read_directive(elf, leaninit_section)
    logging.debug(f'region_size = {format_size(directive.region_size)}')
    logging.debug(f'footer_size = {format_size(directive.footer_size)}')

    print(f'{len(directive.sections_start_addr)} sections to compress.')
    if len(directive.sections_start_addr) == 0:
        logging.warning('Nothing to compress')
        return None

    sections, merged_away = table.collect_sections(elf, directive.sections_start_addr)
    logging.debug(f'sections_to_delete: {merged_away}')
    elf.delete_section(*merged_away)

    print(f'Codec: {the_codec.describe}')
    for section in sections:
        logging.debug(f'Compressing {section.name}')
        section.payload = the_codec.encode(section.data)

    print()
    print('Sections compression summary:')
    print('-' * 77)
    print(f"| {'Name':^16} | {'Size':^16} | {'Compressed size':^16} | {'Gain':^16} |")
    total_gain = 0
    for section in sections:
        gain = len(section.data) - len(section.payload)
        total_gain += gain
        print(
            f'| {section.name:^16} | {format_size(len(section.data)):^16} | '
            f'{format_size(len(section.payload)):^16} | {format_size(gain):^16} |'
        )
    print('-' * 77)
    print(f'Total gain: {format_size(total_gain)}.')

    layout = table.build_table(
        sections,
        pointer_size=pointer_size,
        leaninit_vma=leaninit_section['vma'],
        directive=directive,
        pad_to=pad_to,
        pad_source=pad_source,
        pad_from_content=pad_from_content,
    )

    # host-side check of what the target will walk: every entry decodes back to its section
    parsed = table.parse_table(
        layout.data, pointer_size=pointer_size, leaninit_vma=leaninit_section['vma'], codec=the_codec
    )
    expected = [(s.vma, s.data) for s in sections]
    if parsed.entries != expected:
        raise RuntimeError('table self-check failed: decoded entries differ from the input sections')

    for section in sections:
        if not section.merged:
            elf.delete_section(section.name)

    new_size = len(layout.data)
    org_size = leaninit_section['size']
    if new_size > org_size:
        raise RuntimeError(
            f'compressed table ({new_size} bytes) does not fit in .leaninit ({org_size} bytes): '
            'the load memory is too small for this image'
        )
    used_size = directive.region_size - (org_size - new_size)
    percentage = used_size * 100 / directive.region_size

    print()
    print('Memory usage summary:')
    print('-' * 47)
    print('|   Used size   |  Memory size  | Utilization |')
    print(f'|{format_size(used_size):^14} | {format_size(directive.region_size):^13} | {f"{percentage:.0f}%":^11} |')
    print('-' * 47)
    if pad_to:
        print(f'Padding: {layout.pad_size} bytes, image ends at {layout.image_end:#x} (multiple of {pad_to}).')

    elf.update_section(leaninit_section['name'], data=layout.data)

    if out_elf is not None:
        elf.save_as(out_elf)
        logging.debug(f'result saved as {out_elf}')
    return layout


def main(argv=None):
    scriptname = os.path.basename(__file__)
    parser = argparse.ArgumentParser(scriptname)
    levels = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    parser.add_argument('--log-level', default='INFO', choices=levels)
    parser.add_argument('elf', nargs='?', default=None, help='Path to input elf file', type=str)
    parser.add_argument('prefix', nargs='?', default=None, help='binutils prefix', type=str)
    parser.add_argument('--out-elf', default=None, help='Path to output elf file', type=str)
    parser.add_argument('--codec', default='lz4l', choices=table.CODECS, help='compression codec (default: lz4l)')
    pad = parser.add_argument_group('padding', 'pad the image so that it ends on a fixed boundary')
    pad.add_argument('--pad-to', default=0, type=int, metavar='BYTES', help='boundary the image must end on')
    pad.add_argument(
        '--pad-source',
        default=None,
        metavar='FILE',
        help='file whose first bytes become the pad (commit a random file; required with --pad-to)',
    )
    pad.add_argument(
        '--pad-content-hash',
        action='store_true',
        help='derive the pad from a hash of the table instead (weaker: anything holding the image can recompute it)',
    )
    lz = parser.add_argument_group('lzma-armthumb', 'LZMA1 parameters (defaults are the measured optimum for Thumb-2)')
    d = lzma1.Params()
    lz.add_argument('--lzma-dict-size', default=d.dict_size, type=int)
    lz.add_argument('--lzma-lc', default=d.lc, type=int)
    lz.add_argument('--lzma-lp', default=d.lp, type=int)
    lz.add_argument('--lzma-pb', default=d.pb, type=int)
    lz.add_argument('--lzma-nice-len', default=d.nice_len, type=int)
    lz.add_argument('--lzma-mf', default=d.mf, choices=lzma1.MATCH_FINDERS)
    lz.add_argument('--lzma-depth', default=d.depth, type=int)
    lz.add_argument('--lzma-encoder', default='auto', choices=lzma1.ENCODERS, help='auto prefers the bundled cramjam')
    parser.add_argument(
        '--encoder-info', action='store_true', help='print the LZMA encoder that would be used and exit'
    )

    args = parser.parse_args(argv)
    logformat = '%(asctime)s.%(msecs)03d %(levelname)s:\t%(message)s'
    logdatefmt = '%Y-%m-%d %H:%M:%S'
    logging.basicConfig(level=args.log_level, format=logformat, datefmt=logdatefmt)

    if args.encoder_info:
        print(lzma1.backend_info(args.lzma_encoder))
        return 0
    if args.elf is None or args.prefix is None:
        parser.error('elf and prefix are required')
    if args.pad_to and args.pad_source is None and not args.pad_content_hash:
        parser.error('--pad-to requires --pad-source FILE (or --pad-content-hash)')
    if args.pad_source is not None and args.pad_content_hash:
        parser.error('--pad-source and --pad-content-hash are exclusive')
    pad_source = None
    if args.pad_source is not None:
        with open(args.pad_source, 'rb') as f:
            pad_source = f.read()

    params = lzma1.Params(
        dict_size=args.lzma_dict_size,
        lc=args.lzma_lc,
        lp=args.lzma_lp,
        pb=args.lzma_pb,
        nice_len=args.lzma_nice_len,
        mf=args.lzma_mf,
        depth=args.lzma_depth,
    )
    process_elf(
        args.elf,
        binutils_prefix=args.prefix,
        out_elf=args.out_elf,
        codec=args.codec,
        lzma_params=params,
        lzma_encoder=args.lzma_encoder,
        pad_to=args.pad_to,
        pad_source=pad_source,
        pad_from_content=args.pad_content_hash,
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
