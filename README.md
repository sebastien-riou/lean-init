# lean-init
Compression of initialized data for embedded systems.

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