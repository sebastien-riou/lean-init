# lean-init
Compression of initialized data and/or code for embedded systems.

This is tested against:
- arm-none-eabi-gcc-13.2.1-1.1 (ARM Cortex-M33)
- riscv-none-elf-gcc-13.2.0-2 (RISC-V RV32IC)

## Features

- Two codecs:
  - `lz4l` (default): [lz4](https://lz4.org/) legacy frames at level 9, decoded by a 60-line
    function in `leaninit.h`. Fastest boot, no stack to speak of.
  - `lzma-armthumb`: ARM-Thumb BCJ filter then raw LZMA1 (`lc=1 lp=1 pb=1`, 256 KiB
    dictionary), decoded by the 7-Zip SDK decoder in `leaninit_lzma_armthumb.c`. About 35 %
    smaller than lz4 on Thumb-2 firmware, 10x the decode work, ~7 KiB of decoder code and
    ~10.5 KiB of stack while decoding.
- Optional padding of the image to a fixed boundary (`--pad-to`), for images whose size must be
  a whole number of flash pages.
- Produce a fully debuggable elf file
- User has full control over what is compressed
- Deterministic output: the LZMA encoder is bundled (`cramjam` ships xz statically linked), so
  the compressed bytes depend on the pinned Python packages, not on the host's `liblzma`.
  `python -m leaninit.cli --encoder-info` prints what is in use.

## Installation

### Python package
````
pipenv shell
pip install leaninit
````

### Native dependencies
The python package relies on [binutils](https://www.gnu.org/software/binutils/) to parse/edit elf files.
Binutils package need to match the target CPU.
The `lz4l` codec also needs the [lz4](https://lz4.org/) command line tool; `lzma-armthumb` needs nothing else.

## How to integrate

### LD file
- User add a new section `.leaninit`:
  - It shall be the last section in the load memory.
  - Use `ASCIZ` statement to specify the name of each section to compress.
  - Add `BYTE(0)` to mark the end of the list.
  - Add a `LONG` with the total size of the load memory.
  - Consume the remaining space of the load memory (optional).
- Remove `AT` statement for sections to compress.

Example of `.leaninit` section:

````
/* .leaninit: shall be the last section in FLASH */
.leaninit (READONLY): ALIGN(4)
{
    __leaninit_table = .;
    /* 
    The tool will replace this with the compressed content.
    */

    /* Here we list the sections to compress. You can add more.*/
    ASCIZ ".rodata"
    ASCIZ ".preinit_array?" /* the final ? mark this section as optional, i.e. the tool won't complain if it is not in the elf file */
    ASCIZ ".init_array?"
    ASCIZ ".fini_array?"
    ASCIZ ".text" 
    ASCIZ ".data"

    /* end of list marker, don't change */
    BYTE(0)
        
    /* indicates the total size to the tool for reporting purposes */
    LONG(LENGTH(FLASH))

    /* Optional: 'footer data', i.e. data to place after compressed section */
    LONG(4) /* size of the data: set to 0 if no use */
    LONG(4) /* alignement of the data: set to 0 if no use */
    LONG(0x12345678) /* Optional: the data */

    /* Take all the remaining flash, hoping it is enough */
    . = ORIGIN(FLASH)+LENGTH(FLASH);
} > FLASH
````

### Start up file
- Replace uncompressed initialization loop by a call to the compressed initialization function. 

### C code
- Include `leaninit.h` in `main.c`.

### Build system
- Invoke `leaninit.cli` at the end of the build to generate the final elf file:
  `python -m leaninit.cli <elf> <binutils-prefix> --out-elf <final.elf> [options]`.

### Using the `lzma-armthumb` codec
- Pass `--codec lzma-armthumb` to `leaninit.cli`. The LZMA parameters can be changed with
  `--lzma-dict-size`, `--lzma-lc`, `--lzma-lp`, `--lzma-pb`, `--lzma-nice-len`, `--lzma-mf`,
  `--lzma-depth`; the defaults are the measured optimum for Thumb-2 code and are what the C
  decoder is compiled for (`LEANINIT_LZMA_LC/LP/PB/DICT_SIZE` macros).
- Compile with `-DLEANINIT_CODEC_LZMA_ARMTHUMB` the file that includes `leaninit.h`.
- Add `include/leaninit_lzma_armthumb.c` to the build (copy it next to `leaninit.h` with the
  `lzma/` directory). It runs before any RAM section exists, so build it with
  `-O2 -ffreestanding -fno-builtin -fno-tree-loop-distribute-patterns -fno-stack-protector`
  (no LTO), and make the linker script keep every `.text*` and `.rodata*` input section of
  that object in load memory next to `.leaninit_func`, for example:
  ````
  *(.leaninit_func)
  *leaninit_lzma_armthumb.c.o*(.text .text.* .rodata .rodata.*)
  ````
  `nm -u` on the object must print nothing: the file brings its own `memcpy`/`memset`.
- Stack: about 10.5 KiB while decoding (the LZMA probability model). The decoder never
  returns on a malformed entry; it calls `leaninit_fail(code)`, a weak function that loops
  forever. Define your own (in load memory too) to record the code somewhere first.
- The decode cost is roughly 10x lz4's. On a slow reset clock, raise the core clock before
  calling `leaninit_init()` and restore it afterwards.

### Padding the image
`--pad-to BYTES --pad-source FILE` pads the image, before the footer, so that it ends on a
multiple of `BYTES`. The pad bytes are the first bytes of `FILE`, which is meant to be a
committed file of random bytes: pad that is not derivable from the rest of the image has to be
stored by anything that reproduces the image, which matters when the image is covered by an
attestation. `--pad-content-hash` derives the pad from the table instead; it fixes the geometry
but a program holding the image can recompute it, so it is the weaker option.

## How to test

### Native dependencies
The test use [Renode](https://renode.readthedocs.io/en/latest/index.html).

### Unit tests
````
pip install -e . pytest
pytest
````
They cover the codecs, the table layout and padding, `process_elf` on a small ELF linked with
the host binutils, and the C decoder compiled with the host compiler against the Python
encoder. `lz4`, `gcc`/`cc` and `binutils` must be installed for all of them to run.

### Launching an example test
The `testit_env` scripts build the python package in an isolated environment and then test the basic example for a particular build preset.

````
cd examples/basic
./testit_env minSizeRel
````

## Examples overview

### `basic` example
It is a bare metal application which outputs the full text of Saint Exupery's novel "Le petit prince" on a UART.

In this example, we compress the `.data` section. It contains all initialized variables including the array `petitprince`.

### `whole_fw` example
It is a bare metal application which outputs the full text of Saint Exupery's novel "Le petit prince" on a UART.

In this example, we compress the whole firmware. Everything is compressed except the startup file and the decompressor.
At startup the firmware is decompressed into RAM and executed from there.

## Notes for developpers

### Use the python code from this repo rather than installing from pypi
````
pipenv install
````

### How to publish a release
Just create a release on Github with tag in the format 'vX.Y.Z'. A Github action is then building and uploading it to pypi.