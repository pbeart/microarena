.section .init

.globl _start
_start:
    //mov sp,#0x8000
    lui sp, 0x99991
    call harness