/*
******************************************************************************
**
**  File        : LinkerScript.ld
**
**  Author      : STM32CubeIDE
**
**  Abstract    : Linker script for STM32U5A5xJ Device from STM32U5 series
**                      4096Kbytes FLASH
**                      2512Kbytes RAM
**
**                Set heap size, stack size and stack location according
**                to application requirements.
**
**                Set memory bank area and size if external memory is used.
**
**  Target      : STMicroelectronics STM32
**
**  Distribution: The file is distributed as is without any warranty
**                of any kind.
**
*****************************************************************************
** @attention
**
** Copyright (c) 2024 STMicroelectronics.
** All rights reserved.
**
** This software is licensed under terms that can be found in the LICENSE file
** in the root directory of this software component.
** If no LICENSE file comes with this software, it is provided AS-IS.
**
*****************************************************************************
*/

/* Entry Point */
ENTRY(Reset_Handler)

/* Highest address of the user mode stack */
_estack = ORIGIN(RAM) + LENGTH(RAM); /* end of "RAM" Ram type memory */

_Min_Heap_Size = 0x200; /* required amount of heap */
_Min_Stack_Size = 0x400+2*1024; /* required amount of stack */

/* Memories definition */
MEMORY
{
  RAM   (xrw)   : ORIGIN = 0x20000000, LENGTH = 2496K
  SRAM4 (xrw)   : ORIGIN = 0x28000000, LENGTH = 16K
  FLASH (rx)    : ORIGIN = 0x08000000, LENGTH = 2048K
  DATA_FLASH(r) : ORIGIN = ORIGIN(FLASH) + LENGTH(FLASH), LENGTH = 2048K
}

/* Sections */
SECTIONS
{
  .data_flash :
  {
    . = ALIGN(4);
    KEEP(*(.data_flash))
    . = ALIGN(4);
  } >DATA_FLASH

  /* The startup code into "FLASH" Rom type memory */
  .isr_vector :
  {
    KEEP(*(.isr_vector)) /* Startup code */
    *(.text.Reset_Handler)  /* Startup code */
    *(.leaninit_func)
  } >FLASH

  /* The program code and other data into "FLASH" Rom type memory */
  .text :
  {
    _stext = .;        /* create a global symbol at start */
    *(.text)           /* .text sections (code) */
    *(.text*)          /* .text* sections (code) */
    *(.glue_7)         /* glue arm to thumb code */
    *(.glue_7t)        /* glue thumb to arm code */
    *(.eh_frame)

    KEEP (*(.init))
    KEEP (*(.fini))

    _etext = .;        /* define a global symbols at end of code */
  } >RAM

  /* Constant data into "FLASH" Rom type memory */
  .rodata :
  {
    _srodata = .;      /* create a global symbol at start */
    *(.rodata)         /* .rodata sections (constants, strings, etc.) */
    *(.rodata*)        /* .rodata* sections (constants, strings, etc.) */
  } >RAM

  .ARM.extab (READONLY) : /* The READONLY keyword is only supported in GCC11 and later, remove it if using GCC10 or earlier. */
  {
    _sarmextab = .;        /* create a global symbol at start */
    *(.ARM.extab* .gnu.linkonce.armextab.*)
  } >RAM
  .ARM (READONLY) : /* The READONLY keyword is only supported in GCC11 and later, remove it if using GCC10 or earlier. */
  {
    _sarm = .;        /* create a global symbol at start */
    __exidx_start = .;
    *(.ARM.exidx*)
    __exidx_end = .;
  } >RAM

  .preinit_array (READONLY) : /* The READONLY keyword is only supported in GCC11 and later, remove it if using GCC10 or earlier. */
  {
    _spreinit_array = .;        /* create a global symbol at start */
    PROVIDE_HIDDEN (__preinit_array_start = .);
    KEEP (*(.preinit_array*))
    PROVIDE_HIDDEN (__preinit_array_end = .);
  } >RAM

  .init_array (READONLY) : /* The READONLY keyword is only supported in GCC11 and later, remove it if using GCC10 or earlier. */
  {
    _sinit_array = .;        /* create a global symbol at start */
    PROVIDE_HIDDEN (__init_array_start = .);
    KEEP (*(SORT(.init_array.*)))
    KEEP (*(.init_array*))
    PROVIDE_HIDDEN (__init_array_end = .);
  } >RAM

  .fini_array (READONLY) : /* The READONLY keyword is only supported in GCC11 and later, remove it if using GCC10 or earlier. */
  {
    _sfini_array = .;        /* create a global symbol at start */
    PROVIDE_HIDDEN (__fini_array_start = .);
    KEEP (*(SORT(.fini_array.*)))
    KEEP (*(.fini_array*))
    PROVIDE_HIDDEN (__fini_array_end = .);
  } >RAM

  .version : 
  {
    __version = .;
    KEEP (*(.version))
  } >FLASH

  /* .leaninit: shall be the last section in FLASH and shall be aligned to pointer size */
	.leaninit (READONLY) : ALIGN(4)
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
    ASCIZ ".ARM?"
    ASCIZ ".ARM.extab?"
    ASCIZ ".text" /* Must be after .ARM* */
    ASCIZ ".data"

    /* end of list marker, don't change */
    BYTE(0)
		
    /* indicates the total size to the tool for reporting purposes */
    LONG(LENGTH(FLASH))
    
    /* Optional: data to place after compressed section */
    LONG(16) /* size of the data: set to 0 if no use */
    LONG(16) /* alignement of the data: set to 0 if no use */
    LONG(0) /* Optional: the data */
    LONG(0) /* Optional: the data */
    LONG(0) /* Optional: the data */
    LONG(__version - ORIGIN(FLASH)) /* Optional: the data */

		/* Take all the remaining flash, hoping it is enough */
		. = ORIGIN(FLASH)+LENGTH(FLASH);
	} > FLASH

  /* Initialized data sections into "RAM" Ram type memory */
  .data :
  {
    _sdata = .;        /* create a global symbol at data start */
    *(.data)           /* .data sections */
    *(.data*)          /* .data* sections */
    *(.RamFunc)        /* .RamFunc sections */
    *(.RamFunc*)       /* .RamFunc* sections */

    _edata = .;        /* define a global symbol at data end */
  } >RAM /*AT> FLASH*/

  /* Zero initialized data section into "RAM" Ram type memory */
  .bss :
  {
    /* This is used by the startup in order to initialize the .bss section */
    _sbss = .;         /* define a global symbol at bss start */
    __bss_start__ = _sbss;
    *(.bss)
    *(.bss*)
    *(COMMON)

    _ebss = .;         /* define a global symbol at bss end */
    __bss_end__ = _ebss;
  } >RAM

  /* User_heap_stack section, used to check that there is enough "RAM" Ram type memory left */
  ._user_heap_stack :
  {
    . = ALIGN(8);
    PROVIDE ( end = . );
    PROVIDE ( _end = . );
    . = . + _Min_Heap_Size;
    . = . + _Min_Stack_Size;
    . = ALIGN(8);
  } >RAM

  /* Remove information from the compiler libraries */
  /DISCARD/ :
  {
    libc.a ( * )
    libm.a ( * )
    libgcc.a ( * )
  }

  .ARM.attributes 0 : { *(.ARM.attributes) }
}
