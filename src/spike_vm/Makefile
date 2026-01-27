CC = gcc
CC_RISCV = riscv32-unknown-elf-gcc

CFLAGS = -g -Wall
CFLAGS_RISCV = -g -Og

PY = uv run python

all: build/target extensions/build/filebacked.so extensions/build/mmio_tcp.so

build/mmio.generated.h: struct_mmio.py ../structure_utils.py
	cd ../..; $(PY) -m src.spike_vm.struct_mmio > src/spike_vm/build/mmio.generated.h

build/tcp_mmio_proto.generated.h: struct_tcp_mmio_proto.py ../structure_utils.py
	cd ../..; $(PY) -m src.spike_vm.struct_tcp_mmio_proto > src/spike_vm/build/tcp_mmio_proto.generated.h

extensions/build/mmio_tcp.so: extensions/mmio_tcp.cpp build/tcp_mmio_proto.generated.h
	$(CC) -shared $(CFLAGS) -o extensions/build/mmio_tcp.so -fPIC extensions/mmio_tcp.cpp

extensions/build/filebacked.so: extensions/filebacked.cpp
	$(CC) -shared $(CFLAGS) -o extensions/build/filebacked.so -fPIC extensions/filebacked.cpp

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
	rm -rf extensions/build/*
	rm -rf build/*