#include "build/mmio.generated.h"
#include "harness.h"
#include <assert.h>
#include <stdio.h>

extern int main();

volatile microarena_io_r_t* const mmio_r = (void*)&_Mmap_r_start;


volatile microarena_io_rw_t* const mmio_rw = (void*)&_Mmap_rw_start;

int harness() {
    //asm ("mv sp, %0" : : "r" ((void*)&_Stack_end));
    //int* t = (int*) (0x11110000);
    //setup();
    //*t = 0xdeadbeef;

    //(int*) (0x8000);
    

    //*t = *mm;
    main();
    //z: goto z;
}

const int chunk_max = (sizeof(mmio_rw->putchar_buffer)/sizeof(mmio_rw->putchar_buffer[0]));

int _write(char *data, int size) 
{

    int out_size = (size > chunk_max) ? chunk_max : size;

    for (int i=0; i < out_size; i++) {
        mmio_rw->putchar_buffer[i] = data[i];
    }

    if (out_size < chunk_max - 1) {
        mmio_rw->putchar_buffer[out_size] = 0x0;
    }

    mmio_rw->putchar_go = 0xff;

    return out_size;
}


void log_string(char *string) {
    int l = 0;
    while (string[l] != 0) {
        l++;
    };

    while (l > 0) {
        l -= _write(string, l);
    }
}
void log_int(int i) {
    #define ENOUGH ((8 * sizeof(int) - 1) / 3 + 2)
    char str[ENOUGH];
    sprintf(str, "%d", i);
    log_string(str);
}