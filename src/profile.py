from src.spike_vm import struct_mmio
import yappi
import time
import threading



from src.spike import SpikeSimDriver

struct_r = struct_mmio.microarena_io_r_t()
struct_rw = struct_mmio.microarena_io_rw_t()

s = SpikeSimDriver(struct_rw, struct_r, "./src/spike_vm/memories.lds", "../riscv-isa-sim/build/spike", "rv32imafdc", "./src/spike_vm/extensions/build/mmio_tcp.so", "./src/spike_vm/build/target")

yappi.start()
s.start()
start = time.time()
n = 0
for i in range(40000):
    s.step()
    n += 1
    #print(s.get_mmio_struct_rw())
    if s.get_mmio_struct_rw().stdout_go != 0:
        print("".join(chr(x) for x in s.get_mmio_struct_rw().stdout_buffer))
        break
    #time.sleep(0.01)
t = time.time() - start
print(f"Total time {t} for {n} instructions = {n/t}Hz")

s.tcp_mmio_client.cleanup()

yappi.stop()

# retrieve thread stats by their thread id (given by yappi)
threads = yappi.get_thread_stats()
for thread in threads:
    print(
        "Function stats for (%s) (%d)" % (thread.name, thread.id)
    )  # it is the Thread.__class__.__name__
    yappi.get_func_stats(ctx_id=thread.id).print_all(
        columns={
            0: ("name", 100),
            1: ("ncall", 5),
            2: ("tsub", 8),
            3: ("ttot", 8),
            4: ("tavg", 8)
        }
    )