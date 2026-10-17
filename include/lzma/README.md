# LZMA decoder, 7-Zip SDK 25.01

`LzmaDec.c`, `LzmaDec.h`, `7zTypes.h`, `Compiler.h` and `Precomp.h` are verbatim copies from
the 7-Zip SDK 25.01 (Igor Pavlov, public domain). Nothing else of the SDK is needed for the
single-call decoder `LzmaDecode()`.

Rules kept by `leaninit_lzma_armthumb.c`, which includes `LzmaDec.c` directly:

- `Z7_LZMA_PROB32` stays undefined: probabilities are 16-bit, which halves the stack buffer
  (10,112 bytes for `lc + lp = 2`) and is faster on Cortex-M.
- The decoder is used in its single-call form only, with the destination buffer as the
  dictionary, so the only allocation is the probability array.

To update, replace the five files with the same names from a newer SDK and rerun the tests.
