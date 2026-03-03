.section .init

.globl _start
_start:
    //mov sp,#0x8000
    lui sp, 0x99991
    li x1, 1
    slli x1, x1, 13
    csrrs x0, mstatus, x1
    call harness