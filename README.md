# lean-init
Compression of initialized data and/or code for embedded systems.

This is tested against:
- arm-none-eabi-gcc-13.2.1-1.1 (ARM Cortex-M33)
- riscv-none-elf-gcc-13.2.0-2 (RISC-V RV32IC)

## Features

- Use a fast decompressor ([lz4](https://lz4.org/))
- Produce a fully debuggable elf file
- User has full control over what is compressed

## Installation

### Python package
````
pipenv shell
pip install leaninit
````

### Native dependencies
The python package relies on [lz4](https://lz4.org/) to perform the compression and [binutils](https://www.gnu.org/software/binutils/) to parse/edit elf files.
Binutils package need to match the target CPU.

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

    /* end of table marker, don't change */
    BYTE(0)
        
    /* indicates the total size to the tool for reporting purposes */
    LONG(LENGTH(FLASH))

    /* Take all the remaining flash, hoping it is enough */
    . = ORIGIN(FLASH)+LENGTH(FLASH);
} > FLASH
````

### Start up file
- Replace uncompressed initialization loop by a call to the compressed initialization function. 

### C code
- Include `leaninit.h` in `main.c`.

### Build system
- Invoke `leansys.cli` at the end of the build to generate the final elf file.

## How to test

### Native dependencies
The test use [Renode](https://renode.readthedocs.io/en/latest/index.html).

### Launching a test
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