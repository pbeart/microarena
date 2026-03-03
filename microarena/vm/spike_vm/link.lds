OUTPUT_ARCH( "riscv" )

INCLUDE "memories.lds"

MEMORY {
  ram (rwx) : ORIGIN = RAM_START, LENGTH = RAM_LENGTH
  stack (rw) : ORIGIN = STACK_START, LENGTH = STACK_LENGTH
  mmio_r (rw) : ORIGIN = MMIO_R_START, LENGTH = MMIO_R_LENGTH
  mmio_rw (rw) : ORIGIN = MMIO_RW_START, LENGTH = MMIO_RW_LENGTH
}
ENTRY(_start)
SECTIONS
{
  .stack : {
    . += STACK_LENGTH;
    _Stack_end = .;
  } > stack

  .init : { *(.init*) } > ram
  .text : { *(.text) } > ram
  .data : { *(.data) } > ram

  .memorymapped_r : {
    _Mmap_r_start = .;
    . += MMIO_R_LENGTH;
    _Mmap_r_end = .;
  } > mmio_r = 0xa5

  .memorymapped_rw : {
    _Mmap_rw_start = .;
    . += MMIO_RW_LENGTH;
    _Mmap_rw_end = .;
  } > mmio_rw = 0xa5

}