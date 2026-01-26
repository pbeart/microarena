#define RV_SETUP                                               \
    .section .text.init;                                            \
    .align  6;                                                         \
    la t0, 1f;                                                            \
    csrw mtvec, t0;                                                       \
    /* Set up a PMP to permit all accesses */                             \
    li t0, (1 << (31 + (__riscv_xlen / 64) * (53 - 31))) - 1;             \
    csrw pmpaddr0, t0;                                                    \
    li t0, 0xF;                             \
    csrw pmpcfg0, t0;                                                     \
    .align 2;                                                             \
    1: