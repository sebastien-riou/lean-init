OUTPUT_ARCH( "riscv" )
/* Entry Point */
ENTRY(_start)

/* Highest address of the user mode stack */
_estack = ORIGIN(RAM) + LENGTH(RAM); /* end of "RAM" Ram type memory */

_Min_Heap_Size = 0x200; /* required amount of heap */
_Min_Stack_Size = 0x400+2*1024; /* required amount of stack */

/* Memories definition */
MEMORY
{
  RAM   (xrw)   : ORIGIN = 0x20000000, LENGTH = 512K
  FLASH (rx)    : ORIGIN = 0x00000000, LENGTH = 512K
}

/* Sections */
SECTIONS
{
  /* The program code and other data into "FLASH" Rom type memory */
  .startup :
  {
    *(.startup)
    *(.leaninit_func)
  } >FLASH

  .text :
  {
    *(.text)           /* .text sections (code) */
    *(.text*)          /* .text* sections (code) */
    *(.eh_frame)
    __global_pointer$ = .;

    KEEP (*(.init))
    KEEP (*(.fini))

    _etext = .;        /* define a global symbols at end of code */
  } >RAM

  /* Constant data into "FLASH" Rom type memory */
  .rodata :
  {
    *(.rodata)         /* .rodata sections (constants, strings, etc.) */
    *(.rodata*)        /* .rodata* sections (constants, strings, etc.) */
  } >RAM

  /* .leaninit: shall be the last section in FLASH  and shall be aligned to pointer size */
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
    __bss_start = _sbss;
    *(.bss)
    *(.bss*)
    *(COMMON)

    _ebss = .;         /* define a global symbol at bss end */
    __bss_end = _ebss;
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
}
