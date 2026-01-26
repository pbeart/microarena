CC = gcc
CC_RISCV = riscv32-unknown-elf-gcc

CFLAGS = -g -Wall
CFLAGS_RISCV = -g -Og

PY = uv run python

all: build/target mmu_filebacked/build/filebacked.so

build/mmio.generated.h: mmio_struct.py ../structure_utils.py
	cd ../..; $(PY) -m src.spike_vm.mmio_struct > src/spike_vm/build/mmio.generated.h

mmu_filebacked/build/filebacked.so: mmu_filebacked/filebacked.cpp
	$(CC) -shared $(CFLAGS) -o mmu_filebacked/build/filebacked.so -fPIC mmu_filebacked/filebacked.cpp

build/start.o: start.S
	$(CC_RISCV) $(CFLAGS_RISCV) -x assembler-with-cpp -o build/start.o -c start.S

build/target.o: target.c build/mmio.generated.h
	$(CC_RISCV) $(CFLAGS_RISCV) -o build/target.o -c target.c

build/harness.o: harness.c harness.h build/mmio.generated.h
	$(CC_RISCV) $(CFLAGS_RISCV) -o build/harness.o -c harness.c

build/target: link.lds build/harness.o build/target.o build/start.o
	$(CC_RISCV) $(CFLAGS_RISCV) -T link.lds -nostartfiles -o build/target build/start.o build/harness.o build/target.o

.PHONY: clean 
clean:
	rm -rf mmu_filebacked/build/*
	rm -rf build/*