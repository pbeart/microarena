#pragma once


#include "build/mmio.generated.h"

extern char _Mmap_r_start;
extern char _Mmap_r_end;

extern char _Mmap_rw_start;
extern char _Mmap_rw_end;

extern char _Stack_end;

extern volatile microarena_io_r_t* const mmio_r;
extern volatile microarena_io_rw_t* const mmio_rw;

int harness();

int _write(char *data, int size);

void log_string(char *string);
void log_int(int i);