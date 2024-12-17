import argparse
import logging
import os
import io
import humanfriendly

from leaninit.elf import Elf
from leaninit import lz4l



def process_elf(org_elf_file,*,binutils_prefix,out_elf=None):
    elf = Elf(org_elf_file,binutils_prefix=binutils_prefix)
    pointer_size = elf.addr_width // 8
    leaninit_section = elf.get_section_by_name('.leaninit')
    leaninit_data_bytes = elf.get_section_data(leaninit_section['name'])
    leaninit_data = io.BytesIO(leaninit_data_bytes)
    
    def read_ptr():
        out = int.from_bytes(leaninit_data.read(pointer_size),byteorder=elf.byteorder)
        logging.debug(f'read_ptr: {out}')
        return out
    
    sections_start_addr = []
    logging.debug(f'leaninit_section[\'vma\'] = {leaninit_section['vma']}')
    while True:
        addr = read_ptr()
        if leaninit_section['vma'] == addr:
            break
        sections_start_addr.append(addr)
    region_size = read_ptr()

    print(f'{len(sections_start_addr)} sections to compress.')
    compressed_sections = []

    if 0 == len(sections_start_addr):
        logging.warning('Nothing to compress')
        return 
    
    for lma in sections_start_addr:
        section = elf.get_section_by_lma(lma)
        data = elf.get_section_data(section['name'])
        compressed_data = lz4l.compress(data)[4:] #skip frame descriptor
        compressed_sections.append(
            {
                'name': section['name'],
                'vma': section['vma'],
                'data': data,
                'compressed_data': compressed_data
            }
        )
    
    def format_size(size):
        return humanfriendly.format_size(size,binary=True)

    print()
    print('Sections compression summary:')
    print('-'*77)
    print(f'| {'Name':^16} | {'Size':^16} | {'Compressed size':^16} | {'Gain':^16} |')
    total_gain = 0
    for section in compressed_sections:
        gain = len(section['data']) - len(section['compressed_data'])
        gain_str = format_size(gain)
        size_str = format_size(len(section['data']))
        compressed_size_str = format_size(len(section['compressed_data']))
        total_gain += gain    
        print(f'| {section['name']:^16} | {size_str:^16} | {compressed_size_str:^16} | {gain_str:^16} |')
    print('-'*77)
    print(f'Total gain: {format_size(total_gain)}.')

    final_data = bytearray()
    def write_ptr(addr):
        nonlocal final_data
        final_data = final_data + addr.to_bytes(pointer_size,byteorder='little')
    
    for section in compressed_sections:
        write_ptr(section['vma'])
        final_data += section['compressed_data']
        elf.delete_section(section['name'])
    write_ptr(leaninit_section['vma']) #end marker

    org_size = leaninit_section['size']
    new_size = len(final_data)
    used_size = region_size - (org_size - new_size)
    region_size_str = format_size(region_size)
    used_size_str = format_size(used_size)
    percentage = used_size*100/region_size
    percentage_str = f'{percentage:.0f}%'
    
    print()
    print('Memory usage summary:')
    print('-'*47)
    print('|   Used size   |  Memory size  | Utilization |')
    print(f'|{used_size_str:^14} | {region_size_str:^13} | {percentage_str:^11} |')
    print('-'*47)

    elf.update_section('.leaninit',final_data)
    
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
    process_elf(org_elf_file,binutils_prefix=prefix,out_elf=args.out_elf)