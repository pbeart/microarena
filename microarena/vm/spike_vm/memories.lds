/* This file defines guest memories: it is 1) included in the linker script, */
/* and 2) parsed by the Spike driver to get the right addresses and sizes */
/* for various memories. It therefore must 1) be a valid linker script, and */
/* 2) consist only of blank lines, lines that start with '/*', or lines */
/* containing key-value pairs of the format `\s*KEY\s*=\s*VALUE;\s*` */ 


RAM_START = 0x11110000;
RAM_LENGTH = 0x00010000;

STACK_START = 0x99990000;
STACK_LENGTH = 0x00001000;

MMIO_R_START = 0xdddd000;
MMIO_R_LENGTH = 0x100;

MMIO_RW_START = 0xeeee000;
MMIO_RW_LENGTH = 0x100;
