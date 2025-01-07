import argparse
import copy
import logging
import os
import io
import humanfriendly

from leaninit.elf import Elf
from leaninit import lz4l


def process_elf(org_elf_file, *, binutils_prefix, out_elf=None):
    elf = Elf(org_elf_file, binutils_prefix=binutils_prefix)
    pointer_size = elf.addr_width // 8
    leaninit_section = elf.get_section_by_name('.leaninit')
    leaninit_data_bytes = elf.get_section_data(leaninit_section['name'])
    leaninit_data = io.BytesIO(leaninit_data_bytes)

    def read_ptr():
        out = int.from_bytes(leaninit_data.read(pointer_size), byteorder=elf.byteorder)
        logging.debug(f'read_ptr: {out}')
        return out

    def read_str():
        out = bytearray()
        while True:
            c = leaninit_data.read(1)
            if 0 == c[0]:
                break
            out += c
        out = out.decode()
        logging.debug(f'read_str: {out}')
        return out

    sections_start_addr = []
    # logging.debug(f'leaninit_section[\'vma\'] = {leaninit_section['vma']}')
    # while True:
    #    addr = read_ptr()
    #    if leaninit_section['vma'] == addr:
    #        break
    #    sections_start_addr.append(addr)

    while True:
        name = read_str()
        if 0 == len(name):
            break
        try:
            section = elf.get_section_by_name(name)
            sections_start_addr.append(section['lma'])
        except:
            logging.debug(
                f'section "{name}" not found, assume it has been optimized away'
            )  # assume the section has been removed
    region_size = read_ptr()
    logging.debug(f'region_size = {humanfriendly.format_size(region_size,binary=True)}')

    print(f'{len(sections_start_addr)} sections to compress.')

    if 0 == len(sections_start_addr):
        logging.warning('Nothing to compress')
        return

    sections_end_addr = []
    compressed_sections = []
    for lma in sections_start_addr:
        section = elf.get_section_by_lma(lma)
        data = elf.get_section_data(section['name'])
        section_end_addr = lma + section['size'] - 1
        sections_end_addr.append(section_end_addr)
        compressed_sections.append(
            {
                'name': section['name'],
                'lma': lma,
                'vma': section['vma'],
                'size': len(data),
                'data': data,
                'merged': False,
            }
        )

    # attempt to merge sections
    merged = True
    merge_cnt = 0
    while merged:
        merged = False
        for last in sections_end_addr:
            if last + 1 in sections_start_addr:

                # we can merge those section
                low_addr_index = sections_end_addr.index(last)
                high_addr_index = sections_start_addr.index(last + 1)
                low_addr_lma = sections_start_addr[low_addr_index]
                high_addr_lma = sections_start_addr[high_addr_index]
                low_addr_section = copy.deepcopy(compressed_sections[low_addr_index])
                high_addr_section = copy.deepcopy(compressed_sections[high_addr_index])
                logging.debug(f'Merging {low_addr_section['name']} and {high_addr_section['name']}')

                # remove both original sections
                del sections_start_addr[low_addr_index]
                del sections_end_addr[low_addr_index]
                del compressed_sections[low_addr_index]
                high_addr_index = sections_start_addr.index(last + 1)  # refresh index
                del sections_start_addr[high_addr_index]
                del sections_end_addr[high_addr_index]
                del compressed_sections[high_addr_index]
                elf.delete_section(low_addr_section['name'])
                elf.delete_section(high_addr_section['name'])

                # create the merged sections
                new_last = high_addr_section['lma'] + high_addr_section['size'] - 1
                new_data = low_addr_section['data'] + high_addr_section['data']
                new_size = len(new_data)
                sections_start_addr.append(low_addr_lma)
                sections_end_addr.append(new_last)
                merge_cnt += 1
                new_name = f'.leaninit_merge{merge_cnt}'
                compressed_sections.append(
                    {
                        'name': new_name,
                        'lma': low_addr_lma,
                        'vma': low_addr_section['vma'],
                        'size': new_size,
                        'data': new_data,
                        'merged': True,
                    }
                )
                merged = True

    # compress the sections
    for section in compressed_sections:
        logging.debug(f'Compressing {section['name']}')
        section['compressed_data'] = lz4l.compress(section['data'])[4:]  # skip frame descriptor

    def format_size(size):
        return humanfriendly.format_size(size, binary=True)

    print()
    print('Sections compression summary:')
    print('-' * 77)
    print(f'| {'Name':^16} | {'Size':^16} | {'Compressed size':^16} | {'Gain':^16} |')
    total_gain = 0
    for section in compressed_sections:
        gain = len(section['data']) - len(section['compressed_data'])
        gain_str = format_size(gain)
        size_str = format_size(len(section['data']))
        compressed_size_str = format_size(len(section['compressed_data']))
        total_gain += gain
        print(f'| {section['name']:^16} | {size_str:^16} | {compressed_size_str:^16} | {gain_str:^16} |')
    print('-' * 77)
    print(f'Total gain: {format_size(total_gain)}.')

    final_data = bytearray()

    def write_ptr(addr):
        nonlocal final_data
        final_data = final_data + addr.to_bytes(pointer_size, byteorder='little')

    for section in compressed_sections:
        write_ptr(section['vma'])
        final_data += section['compressed_data']
        if not section['merged']:
            elf.delete_section(section['name'])
    write_ptr(leaninit_section['vma'])  # end marker

    org_size = leaninit_section['size']
    new_size = len(final_data)
    used_size = region_size - (org_size - new_size)
    region_size_str = format_size(region_size)
    used_size_str = format_size(used_size)
    percentage = used_size * 100 / region_size
    percentage_str = f'{percentage:.0f}%'

    print()
    print('Memory usage summary:')
    print('-' * 47)
    print('|   Used size   |  Memory size  | Utilization |')
    print(f'|{used_size_str:^14} | {region_size_str:^13} | {percentage_str:^11} |')
    print('-' * 47)

    elf.update_section('.leaninit', final_data)

    if out_elf is not None:
        elf.save_as(out_elf)


if __name__ == '__main__':
    scriptname = os.path.basename(__file__)
    scriptpath = os.path.dirname(__file__)
    parser = argparse.ArgumentParser(scriptname)
    levels = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    parser.add_argument('--log-level', default='INFO', choices=levels)
    parser.add_argument('elf', default=None, help='Path to input elf file', type=str)
    parser.add_argument('prefix', default=None, help='binutils prefix', type=str)
    parser.add_argument('--out-elf', default=None, help='Path to output elf file', type=str)

    args = parser.parse_args()
    logformat = '%(asctime)s.%(msecs)03d %(levelname)s:\t%(message)s'
    logdatefmt = '%Y-%m-%d %H:%M:%S'
    logging.basicConfig(level=args.log_level, format=logformat, datefmt=logdatefmt)

    prefix = args.prefix
    org_elf_file = args.elf
    process_elf(org_elf_file, binutils_prefix=prefix, out_elf=args.out_elf)
