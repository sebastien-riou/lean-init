
include("${CMAKE_CURRENT_LIST_DIR}/gcc-riscv-none-elf.cmake")
set(CMAKE_SYSTEM_PROCESSOR riscv32)

# Core MCU flags, CPU, instruction set and FPU setup
set(cpu_PARAMS ${cpu_PARAMS}
  -mabi=ilp32 
  -march=rv32ic_zicsr
)