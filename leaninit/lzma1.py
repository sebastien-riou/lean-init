"""Raw LZMA1 encoding with pinned parameters and a bundled encoder.

The encoder matters for reproducible firmware builds: the compressed bytes end up in the
image, so two machines must produce the same stream. ``cramjam`` ships xz statically
linked inside its wheel, so the encoder version follows the package pin rather than the
host's ``liblzma``. The standard library ``lzma`` module is kept as an explicit fallback;
it links whatever ``liblzma`` the interpreter was built against.

Decoding always uses the standard library: decoders are stable across versions and it
keeps the self-checks independent of the encoder.
"""

import importlib.metadata
import lzma
from dataclasses import dataclass

ENCODERS = ('auto', 'cramjam', 'stdlib')
MATCH_FINDERS = ('bt2', 'bt3', 'bt4', 'hc3', 'hc4')

# Raw xz encoding is broken in older cramjam releases: 2.9 to 2.13 reject every raw LZMA1
# stream with "liblzma internal error". 2.14 is the first one that works.
CRAMJAM_MIN_VERSION = (2, 14)


@dataclass(frozen=True)
class Params:
    """LZMA1 parameters. The defaults are the measured optimum for Thumb-2 firmware."""

    dict_size: int = 256 * 1024
    lc: int = 1
    lp: int = 1
    pb: int = 1
    nice_len: int = 273
    mf: str = 'bt4'
    depth: int = 512

    def __post_init__(self):
        if not (0 <= self.lc <= 8 and 0 <= self.lp <= 4 and 0 <= self.pb <= 4):
            raise ValueError(f'lc/lp/pb out of range: {self.lc}/{self.lp}/{self.pb}')
        if self.lc + self.lp > 4:
            raise ValueError(f'lc + lp must not exceed 4 (got {self.lc + self.lp})')
        if self.mf not in MATCH_FINDERS:
            raise ValueError(f'unknown match finder {self.mf!r}, expected one of {MATCH_FINDERS}')
        if not (4096 <= self.dict_size <= (1 << 30)):
            raise ValueError(f'dict_size out of range: {self.dict_size}')

    def props(self) -> bytes:
        """The 5-byte LZMA properties header: lc/lp/pb byte then the dictionary size."""
        return bytes([(self.pb * 5 + self.lp) * 9 + self.lc]) + self.dict_size.to_bytes(4, 'little')

    @staticmethod
    def from_props(props: bytes) -> 'Params':
        if len(props) != 5 or props[0] >= 9 * 5 * 5:
            raise ValueError(f'invalid LZMA properties {props.hex()}')
        d, lc = divmod(props[0], 9)
        pb, lp = divmod(d, 5)
        return Params(dict_size=int.from_bytes(props[1:5], 'little'), lc=lc, lp=lp, pb=pb)

    @property
    def num_probs(self) -> int:
        """Size of the decoder's probability model, in 16-bit entries (7-Zip SDK formula)."""
        return 1984 + (0x300 << (self.lc + self.lp))


_STDLIB_MF = {
    'bt2': lzma.MF_BT2,
    'bt3': lzma.MF_BT3,
    'bt4': lzma.MF_BT4,
    'hc3': lzma.MF_HC3,
    'hc4': lzma.MF_HC4,
}


def _stdlib_filter(p: Params) -> dict:
    return {
        'id': lzma.FILTER_LZMA1,
        'dict_size': p.dict_size,
        'lc': p.lc,
        'lp': p.lp,
        'pb': p.pb,
        'nice_len': p.nice_len,
        'mf': _STDLIB_MF[p.mf],
        'depth': p.depth,
        'mode': lzma.MODE_NORMAL,
    }


def _cramjam():
    try:
        import cramjam
    except ImportError as e:
        raise RuntimeError('the cramjam package is required for the bundled LZMA encoder') from e
    version = tuple(int(x) for x in cramjam.__version__.split('.')[:2])
    if version < CRAMJAM_MIN_VERSION:
        wanted = '.'.join(str(x) for x in CRAMJAM_MIN_VERSION)
        raise RuntimeError(
            f'cramjam {cramjam.__version__} cannot produce raw LZMA1 streams, {wanted} or newer is required'
        )
    return cramjam


def _compress_cramjam(data: bytes, p: Params) -> bytes:
    xz = _cramjam().xz
    mf = {
        'bt2': xz.MatchFinder.BinaryTree2,
        'bt3': xz.MatchFinder.BinaryTree3,
        'bt4': xz.MatchFinder.BinaryTree4,
        'hc3': xz.MatchFinder.HashChain3,
        'hc4': xz.MatchFinder.HashChain4,
    }[p.mf]
    opts = xz.Options()
    opts.set_dict_size(p.dict_size)
    opts.set_lc(p.lc)
    opts.set_lp(p.lp)
    opts.set_pb(p.pb)
    opts.set_nice_len(p.nice_len)
    opts.set_mf(mf)
    opts.set_mode(xz.Mode.Normal)
    opts.set_depth(p.depth)
    chain = xz.FilterChain()
    chain.append_filter(xz.FilterChainItem(xz.Filter.Lzma1, opts))
    return bytes(xz.compress(data, format=xz.Format.RAW, filters=chain))


def _compress_stdlib(data: bytes, p: Params) -> bytes:
    return lzma.compress(data, format=lzma.FORMAT_RAW, filters=[_stdlib_filter(p)])


def resolve_encoder(encoder: str = 'auto') -> str:
    if encoder not in ENCODERS:
        raise ValueError(f'unknown encoder {encoder!r}, expected one of {ENCODERS}')
    if encoder == 'auto':
        try:
            _cramjam()
            return 'cramjam'
        except RuntimeError:
            return 'stdlib'
    return encoder


def compress_raw(data: bytes, p: Params | None = None, encoder: str = 'auto') -> bytes:
    """A raw LZMA1 stream (no container, with an end-of-payload marker) for ``data``."""
    p = p or Params()
    name = resolve_encoder(encoder)
    if name == 'cramjam':
        return _compress_cramjam(data, p)
    return _compress_stdlib(data, p)


def decompress_raw(stream: bytes, p: Params, size: int) -> bytes:
    """Decode ``size`` bytes from a raw LZMA1 stream with the standard library, strictly.

    Raises if the stream does not decode to exactly ``size`` bytes, is not finished, or
    leaves unused input: those are the conditions the C decoder also refuses.
    """
    d = lzma.LZMADecompressor(
        format=lzma.FORMAT_RAW,
        filters=[{'id': lzma.FILTER_LZMA1, 'dict_size': p.dict_size, 'lc': p.lc, 'lp': p.lp, 'pb': p.pb}],
    )
    out = d.decompress(stream, max_length=size)
    if len(out) != size:
        raise ValueError(f'stream decodes to {len(out)} bytes, expected {size}')
    if not d.eof:
        # drain: a well-formed stream ends with its marker right after the last byte
        tail = d.decompress(b'', max_length=1)
        if tail or not d.eof:
            raise ValueError('stream is not finished after the expected number of bytes')
    if d.unused_data:
        raise ValueError(f'{len(d.unused_data)} unused bytes after the end of the stream')
    return out


def backend_info(encoder: str = 'auto') -> str:
    """Human-readable name and version of the encoder that ``compress_raw`` would use."""
    name = resolve_encoder(encoder)
    if name == 'cramjam':
        return f'cramjam {importlib.metadata.version("cramjam")} (xz statically linked)'
    return f'python stdlib lzma (system liblzma, {_liblzma_version()})'


def _liblzma_version() -> str:
    try:
        import ctypes

        lib = ctypes.CDLL('liblzma.so.5')
        lib.lzma_version_string.restype = ctypes.c_char_p
        return lib.lzma_version_string().decode()
    except Exception:
        return 'version unknown'
