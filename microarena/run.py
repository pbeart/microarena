
from microarena.game import sim
from microarena.vm.spike import SpikeSimDriver
from microarena.vm.spike_vm.struct_mmio import microarena_io_r_t, microarena_io_rw_t
from microarena.vm.mmio_ship_driver import MMIOStructShipDriver

g = sim.Game()


ship_b_driver = sim.InputShipDriver()

mmio_r = microarena_io_r_t()
mmio_rw = microarena_io_rw_t()

ship_a_vm = SpikeSimDriver(microarena_io_rw_t(), microarena_io_r_t(), "./microarena/vm/spike_vm/memories.lds", "../riscv-isa-sim/build/spike", "rv32imafdc", "./microarena/vm/spike_vm/extensions/build/mmio_tcp.so", "./microarena/vm/spike_vm/build/target")
ship_a_driver = MMIOStructShipDriver()#sim.RandomShipDriver()

ship_a_vm.get_mmio_struct_rw()

ship_a_vm.start()

while g.frame():
    for i in range(20):
        ship_a_vm.step()
    r = ship_a_vm.get_mmio_struct_r()
    rw = ship_a_vm.get_mmio_struct_rw()

    ship_a_driver.update((g.match.ship_a, rw, r))

    ship_a_vm.set_mmio_struct_r(r)
    ship_a_vm.set_mmio_struct_rw(rw)

    ship_b_driver.update((g.match.ship_b, g.match.input_state))

    