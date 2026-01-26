#include "harness.h"
#include <stdio.h>

//int __attribute__ ((noinline)) sub(int a) {
//    return a+1;
//}

int main() {
    //asm ("mv sp, %0" : : "r" (0x69));
    //mmio_rw->a = 0x69;
    //int c = mmio_r->b;
    //char a[10] = "Hello eve";
    //for (int i=0; i<10; i++) {
    //    mmio_rw->stdout_buffer[i] = a[i];
    //};
    //mmio_rw->stdout_go = 0xff;
    log_string("Hello world!\n");
    //_write(0, a, 10);
    //printf("Hi!\n");
    //int x = sub(5);
}