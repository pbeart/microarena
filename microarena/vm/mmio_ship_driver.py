
from ..game import entitydriver
from ..game import sim
from ..vm.spike_vm import struct_mmio

class MMIOStructShipDriver(entitydriver.EntityDriver):
    def update(self, on: tuple[sim.Ship, struct_mmio.microarena_io_rw_t, struct_mmio.microarena_io_r_t]):
        ship = on[0]
        

        struct_r = on[2] # the guest reads from this

        # INPUT: reading ship values
        struct_r.angle = ship.angle
        struct_r.angle_rate = ship.angular_velocity

        struct_r.speed = ship.velocity.length
        
        struct_r.radar_d = ship.radar_state.distance

        if ship.radar_state.freq == sim.RadarFreq.NONE:
            struct_r.radar_f = struct_mmio.RADAR_FREQ_NONE.value
        elif ship.radar_state.freq == sim.RadarFreq.PROJECTILE:
            struct_r.radar_f = struct_mmio.RADAR_FREQ_PROJECTILE.value
        elif ship.radar_state.freq == sim.RadarFreq.SHIP:
            struct_r.radar_f = struct_mmio.RADAR_FREQ_SHIP.value
        elif ship.radar_state.freq == sim.RadarFreq.WALL:
            struct_r.radar_f = struct_mmio.RADAR_FREQ_WALL.value
            

        # OUTPUT: driving the ship

        struct_rw = on[1] # the guest writes to this, and could read from it

        if struct_rw.shoot:
            ship.shoot = True
            struct_rw.shoot = False

        ship.thrusting = struct_rw.thrust

        if struct_rw.turn == struct_mmio.TURN_LEFT.value:
            ship.turn = sim.TurnDirection.Left
        elif struct_rw.turn == struct_mmio.TURN_RIGHT.value:
            ship.turn = sim.TurnDirection.Right
        else:
            ship.turn = sim.TurnDirection.No


        if struct_rw.putchar_go:
            #print(struct_rw.putchar_buffer)
            #print([repr(x) for x in struct_rw.putchar_buffer])
            print("LOG: ", end="")
            for x in struct_rw.putchar_buffer:
                if x == 0: break
                print(chr(x), end="")
            print("")

            struct_rw.putchar_go = 0
        #struct_r.radar_d = ship.
