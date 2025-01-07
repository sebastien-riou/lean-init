import logging
import os
import re
import shutil
import subprocess
import tempfile


class SectionNameNotFoundError(RuntimeError):
    pass


class Elf:
    @staticmethod
    def invoke_tool(cmd):
        try:
            res = subprocess.run(cmd, capture_output=True, check=True, shell=False)  # noqa: S603
            outstr = res.stdout.decode()
            logging.debug(outstr)
            logging.debug(res.stderr.decode())
        except subprocess.CalledProcessError as e:
            nl = '\n'
            logging.debug(f'{cmd[0]} failed')
            logging.debug(f'arguments: {e.args!s}')
            logging.debug(f'stdout{nl}{e.stdout}')
            logging.debug(f'stderr{nl}{e.stderr}')
            logging.debug(f'return code: {e.returncode}')
            raise
        return outstr

    @staticmethod
    def get_tmp_file():
        file = os.path.join(tempfile.mkdtemp(), 'elf.tmp')
        return file

    def read_file_format(self):
        outstr = self.objdump(self._elf_file, '-a')
        info_line = r'\s*\S+:\s+file format\s+(\S+)'
        m = re.search(info_line, outstr)
        self._file_format = m.group(1)
        logging.debug(f'file format is "{self._file_format}"')
        parts = self._file_format.split('-')
        match parts[0]:
            case 'elf32':
                self._addr_width = 32
            case 'elf64':
                self._addr_width = 64
            case _:
                logging.warning(f'could not identify address width, file format is "{self._file_format}"')
        logging.debug(f'address width is "{self._addr_width}"')

        match parts[1]:
            case 'littlearm':
                self._byteorder = 'little'
            case 'littleriscv':
                self._byteorder = 'little'
            case 'bigarm':
                self._byteorder = 'big'
            case 'bigriscv':
                self._byteorder = 'big'
            case _:
                logging.warning(f'could not identify endianess, file format is "{self._file_format}"')
        logging.debug(f'byteorder is "{self._byteorder}"')

        return self._file_format

    def read_sections(self) -> list:
        out = []
        outstr = self.objdump(self._elf_file, '-h')
        section_info = (
            r'\d+\s+(\S+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+2\*\*(\d+)\s*\n(.*)'
        )
        for m in re.finditer(section_info, outstr):
            flags = m.group(7).strip().split(',')
            flags = [s.strip() for s in flags]
            section = {
                'name': m.group(1),
                'size': int(m.group(2), 16),
                'vma': int(m.group(3), 16),
                'lma': int(m.group(4), 16),
                'file-offset': int(m.group(5), 16),
                'align': 2 ** int(m.group(6)),
                'flags': flags,
            }
            logging.debug(section)
            out.append(section)
        self._sections = out
        return out

    @property
    def addr_width(self):
        if self._addr_width is None:
            self.read_file_format()
        return self._addr_width

    @property
    def byteorder(self):
        if self._byteorder is None:
            self.read_file_format()
        return self._byteorder

    @property
    def file_format(self):
        if self._file_format is None:
            self.read_file_format()
        return self._file_format

    @property
    def sections(self):
        if self._sections is None:
            self.read_sections()
        return self._sections

    def __init__(self, elf, *, binutils_prefix='riscv-none-elf-'):
        self._elf_file = elf
        self._binutils_prefix = binutils_prefix
        self._objdump_path = shutil.which(binutils_prefix + 'objdump')
        self._objcopy_path = shutil.which(binutils_prefix + 'objcopy')
        self._addr_width = None
        self._byteorder = None
        self._file_format = None
        self._sections = None

    def objdump(self, *args) -> str:
        cmd = [self._objdump_path, *args]
        return self.invoke_tool(cmd)

    def objcopy(self, *args) -> str:
        cmd = [self._objcopy_path, *args]
        return self.invoke_tool(cmd)

    def get_section_names(self) -> list:
        names = [n['name'] for n in self._sections]
        return names

    def get_section_by_name(self, name):
        try:
            return next(filter(lambda section: section['name'] == name, self.sections))
        except StopIteration as e:
            raise SectionNameNotFoundError(f'section "{name}" not found') from e

    def get_section_by_vma(self, vma):
        return next(filter(lambda section: section['vma'] == vma, self.sections))

    def get_section_by_lma(self, lma):
        return next(filter(lambda section: section['lma'] == lma, self.sections))

    def get_section_data(self, name) -> bytes:
        names = self.get_section_names()
        if name not in names:
            raise SectionNameNotFoundError(f'section "{name}" not found')
        section = self.get_section_by_name(name)
        if 'CONTENTS' not in section['flags']:
            return bytearray(section['size'])
        tmpfile = self.get_tmp_file()
        self.objcopy(self._elf_file, '--dump-section', name + '=' + tmpfile)
        data = open(tmpfile, 'rb').read()
        os.remove(tmpfile)
        return data

    def delete_section(self, name):
        self._sections = None
        outfile = self.get_tmp_file()
        try:
            self.objcopy(self._elf_file, '--remove-section', name, outfile)
        except subprocess.CalledProcessError as e:
            names = self.get_section_names()
            if name not in names:
                raise SectionNameNotFoundError(f'section "{name}" not found') from e
            raise
        self._elf_file = outfile

    def update_section(self, name, data):
        self._sections = None
        tmpfile = self.get_tmp_file()
        with open(tmpfile, 'wb') as f:
            f.write(data)
        outfile = self.get_tmp_file()
        try:
            self.objcopy(self._elf_file, '--update-section', name + '=' + tmpfile, outfile)
        except subprocess.CalledProcessError as e:
            names = self.get_section_names()
            if name not in names:
                raise SectionNameNotFoundError(f'section "{name}" not found') from e
            raise
        self._elf_file = outfile

    def save_as(self, dst_path):
        shutil.copy(self._elf_file, dst_path)
        self._elf_file = dst_path
