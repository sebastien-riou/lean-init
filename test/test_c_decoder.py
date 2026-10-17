"""The C decoder (include/leaninit_lzma_armthumb.c) against the Python encoder, on the host.

Compiled with the host C compiler using the same freestanding flags an integrator uses, so a
synthesised libc call or a stray constant table shows up here as a link or run failure.
"""

import os
import shutil
import subprocess

import pytest
from helpers import random_bytes, thumb_like

from leaninit import lzma1, lzma_armthumb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCLUDE = os.path.join(ROOT, 'include')
FREESTANDING = ['-ffreestanding', '-fno-builtin', '-fno-tree-loop-distribute-patterns', '-fno-stack-protector']


@pytest.fixture(scope='module')
def host_decode(tmp_path_factory):
    cc = shutil.which('cc') or shutil.which('gcc') or shutil.which('clang')
    if cc is None:
        pytest.skip('no host C compiler')
    d = tmp_path_factory.mktemp('cdec')
    glue = os.path.join(d, 'glue.o')
    exe = os.path.join(d, 'host_decode')
    subprocess.run(
        [
            cc,
            '-O2',
            '-std=gnu11',
            '-Wall',
            '-Wextra',
            '-Werror',
            *FREESTANDING,
            '-I',
            INCLUDE,
            '-c',
            os.path.join(INCLUDE, 'leaninit_lzma_armthumb.c'),
            '-o',
            glue,
        ],
        check=True,
    )
    subprocess.run(
        [cc, '-O2', '-std=gnu11', '-Wall', os.path.join(ROOT, 'test', 'c', 'host_decode.c'), glue, '-o', exe],
        check=True,
    )
    return exe


def run_decoder(exe, entry: bytes, tmp_path):
    ent = tmp_path / 'entry.bin'
    out = tmp_path / 'out.bin'
    ent.write_bytes(entry)
    r = subprocess.run([exe, str(ent), str(out)], capture_output=True, text=True)
    data = out.read_bytes() if out.exists() else None
    return r.returncode, data, r.stdout.strip(), r.stderr.strip()


@pytest.mark.parametrize(
    'data',
    [thumb_like(50000, 1), random_bytes(10000, 2), b'', b'\x00' * 70000, thumb_like(3, 3)],
    ids=['thumb', 'random', 'empty', 'zeros', 'tiny'],
)
def test_c_decoder_matches_python_encoder(host_decode, tmp_path, data):
    entry = lzma_armthumb.encode_entry(data)
    rc, back, consumed, err = run_decoder(host_decode, entry + b'trailing bytes', tmp_path)
    assert rc == 0, err
    assert back == data
    assert int(consumed) == len(entry)


def test_c_decoder_refuses_other_props(host_decode, tmp_path):
    entry = lzma_armthumb.encode_entry(thumb_like(1000, 4), lzma1.Params(lc=0, lp=2, pb=1))
    rc, _, _, err = run_decoder(host_decode, entry, tmp_path)
    assert rc == 2 and 'leaninit_fail(0x1)' in err


def test_c_decoder_refuses_reserved_bytes(host_decode, tmp_path):
    entry = bytearray(lzma_armthumb.encode_entry(thumb_like(1000, 4)))
    entry[15] = 1
    rc, _, _, err = run_decoder(host_decode, bytes(entry), tmp_path)
    assert rc == 2 and 'leaninit_fail(0x1)' in err


def test_c_decoder_refuses_truncated_stream(host_decode, tmp_path):
    data = thumb_like(20000, 5)
    entry = bytearray(lzma_armthumb.encode_entry(data))
    # keep the header's compressed_len, hand the decoder a stream that ends early with junk after it
    cut = len(entry) - 40
    bad = bytes(entry[:cut]) + bytes(40)
    rc, _back, _, err = run_decoder(host_decode, bad, tmp_path)
    assert rc == 2, 'the decoder accepted a damaged stream'
    assert 'leaninit_fail(' in err


def test_c_decoder_refuses_short_length(host_decode, tmp_path):
    data = thumb_like(20000, 6)
    entry = bytearray(lzma_armthumb.encode_entry(data))
    entry[4:8] = (len(data) - 1).to_bytes(4, 'little')  # claims one byte fewer than the stream holds
    rc, _, _, err = run_decoder(host_decode, bytes(entry), tmp_path)
    assert rc == 2
    assert 'leaninit_fail(' in err
