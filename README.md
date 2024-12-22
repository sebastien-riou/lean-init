# lean-init
Compression of initialized data for embedded systems.

## Features

- Use a fast decompressor ([lz4](https://lz4.org/))
- Produce a fully debuggable elf file

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
- User add a new section `.leaninit` and specify in it which sections shall be compressed.
- Remove `AT` statement for sections to compress.

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