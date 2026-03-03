from dataclasses import dataclass
from enum import Enum
import math
import os
import random
from typing import Literal, Sequence, Union, cast
import pygame
import pymunk.pygame_util

from abc import abstractmethod

from . import entitydriver


class RandomShipDriver(entitydriver.EntityDriver):
    def update(self, on: "Ship"):
        
        if random.random() < 0.05:
            on.thrusting = not on.thrusting

        if random.random() < 0.02:
            on.shoot = True

class InputShipDriver(entitydriver.EntityDriver):
    def update(self, on: tuple["Ship", "InputState"]):
        ship = on[0]
        input = on[1]

        ship.thrusting = input.thrust
        ship.shoot = input.shoot
        ship.turn = TurnDirection.No
        if input.turn_left: ship.turn = TurnDirection.Left
        if input.turn_right: ship.turn = TurnDirection.Right
        

class DrawFrameHandled:
    @abstractmethod
    def draw_frame(self, surface: pygame.Surface) -> bool:
        pass

class PolyBody[T: pymunk.Poly](pymunk.Body):
    def __init__(self):
        self.deleted = False
        super().__init__()

    def delete(self):
        if self.space is not None:
            self.space.remove(self)
        
        if self.poly.space is not None:
            self.poly.space.remove(self.poly)

        self.deleted = True 

@dataclass
class ShipProperties:
    max_thrust: float
    max_torque: float
    radar_range: float
    mass: float
    width: float
    height: float
    starting_health: float

default_ship_properties = ShipProperties(
    max_thrust = 7000.0,
    max_torque = 90000.0,
    radar_range = 140.0,
    mass = 100.0,
    width = 40,
    height = 30,
    starting_health = 5
)


class CollisionLayer(Enum):
    SHIP = 1
    PROJECTILE = 2
    WALL = 3


class CategoryMask(Enum):
    SHIP = 1
    PROJECTILE = 2
    WALL = 4
    GHOST = 8

SHAPE_FILTER_RADAR = pymunk.ShapeFilter(
    mask=CategoryMask.SHIP.value & CategoryMask.PROJECTILE.value & CategoryMask.WALL.value
)

SHAPE_FILTER_SHIP = pymunk.ShapeFilter(
    categories=CategoryMask.SHIP.value
)

SHAPE_FILTER_PROJECTILE = pymunk.ShapeFilter(
    categories=CategoryMask.PROJECTILE.value
)

SHAPE_FILTER_GHOST = pymunk.ShapeFilter(
    categories=CategoryMask.GHOST.value
)

SHAPE_FILTER_WALL = pymunk.ShapeFilter(
    categories=CategoryMask.WALL.value
)

class MapCellSpecial(Enum):
    SPAWN_A = "a"
    SPAWN_B = "b"

class MapCell(Enum):
    EMPTY = " "
    WALL = "#"
    
    SLOPE_BR = "/"
    SLOPE_BL = "\\"
    SLOPE_TR = "`"
    SLOPE_TL = "*"

map = r"""
#############################
#*                         `#
#                           #
#                           #
#               \           #
#               #           #
#               ###\        #
#                           #
#                           #
#                           #
#                           #
#     ##*             #     #
#     #      /#\      #  b  #
#     #      ###      #     #
#  a  #      `#*      #     #
#     #             /##     #
#                           #
#                           #
#                           #
#                           #
#        `###               #
#           #               #
#           `               #
#                           #
#                           #  
#\                         /#
#############################
"""

base = os.path.dirname(__file__)

SOUND_FILE_PROJECTILE_EXPLODE = os.path.join(base, "./audio/rocket sfx Projectile Explodes.wav")
SOUND_FILE_ROCKET_MAIN = os.path.join(base, "./audio/rocket sfx Rocket Main.wav")
SOUND_FILE_ROCKET_MANEUVER = os.path.join(base, "./audio/rocket sfx Rocket Maneuver.wav")
SOUND_FILE_RADAR_SHIP = os.path.join(base, "./audio/rocket sfx Radar Sees Ship.wav")


class Map(DrawFrameHandled):
    cell_width = 20
    cell_height = 20

    @staticmethod
    def _process_map_string(string: str) -> list[list[MapCell|MapCellSpecial]]:
        out = []
        for line in string.splitlines():
            if line == "": continue

            def map_cell_or_special(s: str):
                try:
                    return MapCellSpecial(s)
                except ValueError:
                    return MapCell(s)
                
            out.append(
                [map_cell_or_special(char) for char in line]
            )
        
        return out
    
    def add_body_for_complex_cell(self, cell: Literal[MapCell.SLOPE_BL] | Literal[MapCell.SLOPE_BR] | Literal[MapCell.SLOPE_TL] | Literal[MapCell.SLOPE_TR], position: pymunk.Vec2d):
        body = pymunk.Body(body_type=pymunk.Body.STATIC)

        if cell == MapCell.SLOPE_BR: # /
            polygon = [
                (self.cell_width, 0),
                (self.cell_width, self.cell_height),
                (0, self.cell_height)
            ]
        elif cell == MapCell.SLOPE_BL: # \
            polygon = [
                (0, 0),
                (self.cell_width, self.cell_height),
                (0, self.cell_height)
            ]
        elif cell == MapCell.SLOPE_TR: # `
            polygon = [
                (0, 0),
                (self.cell_width, 0),
                (self.cell_width, self.cell_height)
            ]
        elif cell == MapCell.SLOPE_TL: # *
            polygon = [
                (0, 0),
                (self.cell_width, 0),
                (0, self.cell_height)
            ]
        else: raise ValueError(cell)

        shape = pymunk.Poly(body, polygon)
        shape.filter = SHAPE_FILTER_WALL
        shape.collision_type = CollisionLayer.WALL.value

        body.position = position

        self.space.add(body, shape)
    
    def add_bodies_for_map(self):
        "Slightly more efficient than one body per cell using RLE on rows"

        def _commit_run(run, this_x, this_y):
            if run == 0: return
            body = pymunk.Body(body_type=pymunk.Body.STATIC)
            shape = pymunk.Poly(
                body, 
                [
                    (0, 0),
                    (run * self.cell_width, 0),
                    (run * self.cell_width, self.cell_height),
                    (0, self.cell_height)
                ]
            )
            shape.filter = SHAPE_FILTER_WALL
            shape.collision_type = CollisionLayer.WALL.value

            body.position = pymunk.Vec2d(this_x - run * self.cell_width, this_y)
            self.space.add(body, shape)

        for yi, row in enumerate(self.map):
            y = yi*self.cell_height
            run = 0
            xi = 0
            while xi < len(row):
                char = row[xi]

                x = xi*self.cell_width

                if char == MapCell.WALL:
                    run += 1
                else:
                    if char != MapCell.EMPTY:
                        # add this non-wall body
                        self.add_body_for_complex_cell(char, pymunk.Vec2d(x,y))

                    # commit any run
                    _commit_run(run, x, y)
                    run = 0

                xi += 1
                    
            _commit_run(run, len(row) * self.cell_width, y)

    def __init__(self, string: str, space: pymunk.Space):
        self.space = space
        map_with_specials = self._process_map_string(string)

        spawn_a = None
        spawn_b = None
        self.map = []

        for iy, row in enumerate(map_with_specials):
            y = iy * self.cell_height
            row_out = []
            for ix, cell in enumerate(row):
                x = ix * self.cell_width
                if isinstance(cell, MapCellSpecial):
                    if cell == MapCellSpecial.SPAWN_A:
                        spawn_a = (x, y)
                    elif cell == MapCellSpecial.SPAWN_B:
                        spawn_b = (x, y)
                    row_out.append(MapCell.EMPTY)
                else:
                    row_out.append(cell)
            
            self.map.append(row_out)

        assert spawn_a is not None
        self.spawn_a = spawn_a

        assert spawn_b is not None
        self.spawn_b = spawn_b


        self.add_bodies_for_map()
        
    def draw_frame(self, surface):
        for yi, row in enumerate(self.map):
            for xi, char in enumerate(row):
                x = xi*self.cell_width
                y = yi*self.cell_height

                if char == MapCell.EMPTY:
                    polygon = None
                elif char == MapCell.WALL:
                    polygon = [
                        (x, y),
                        (x + self.cell_width, y),
                        (x + self.cell_width, y + self.cell_height),
                        (x, y + self.cell_height)
                    ]
                elif char == MapCell.SLOPE_BR: # /
                    polygon = [
                        (x + self.cell_width, y),
                        (x + self.cell_width, y + self.cell_height),
                        (x, y + self.cell_height)
                    ]
                elif char == MapCell.SLOPE_BL: # \
                    polygon = [
                        (x, y),
                        (x + self.cell_width, y + self.cell_height),
                        (x, y + self.cell_height)
                    ]
                elif char == MapCell.SLOPE_TR: # `
                    polygon = [
                        (x, y),
                        (x + self.cell_width, y),
                        (x + self.cell_width, y + self.cell_height)
                    ]
                elif char == MapCell.SLOPE_TL: # *
                    polygon = [
                        (x, y),
                        (x + self.cell_width, y),
                        (x, y + self.cell_height)
                    ]
                else: raise ValueError(char)

                if polygon is not None:
                    pygame.draw.polygon(
                        surface,
                        pygame.Color(128, 128, 128),
                        polygon
                    )
        return True

class RadarFreq(Enum):
    NONE = 0
    WALL = 1
    PROJECTILE = 2
    SHIP = 3

class TurnDirection(Enum):
    No = 0
    Left = 1
    Right = 2

@dataclass
class RadarState:
    freq: RadarFreq
    distance: float

class Ship(PolyBody, DrawFrameHandled):
    def __init__(self, space: pymunk.Space, properties: ShipProperties, match: "Match", color: pygame.Color):
        super().__init__()
        self.match = match
        self._max_thrust = properties.max_thrust
        self._max_torque = properties.max_torque

        self.radar_state = RadarState(RadarFreq.NONE, 0)
        self.color = color

        self.width = properties.width
        self.height = properties.height
        self.width = properties.width

        self.poly = pymunk.Poly.create_box(self, size=(properties.width, properties.height))
        self.poly.mass = properties.mass
        self.poly.filter = SHAPE_FILTER_SHIP
        #self.poly.color = pygame.Color("red")
        self.poly.collision_type = CollisionLayer.SHIP.value
        

        self.radar_range = properties.radar_range

        self.sound_detect_ship = pygame.mixer.Sound(SOUND_FILE_RADAR_SHIP)
        

        self.angle = 0.0

        self.thrusting = True

        self.turn = TurnDirection.No

        self.shoot = False

        space.add(self, self.poly)

        self._health = properties.starting_health

        self.take_damage_frames = 0

        self.sound_rocket_main = pygame.mixer.Sound(SOUND_FILE_ROCKET_MAIN)


    def start_taking_damage(self):
        self.take_damage_frames = 40


    def take_damage(self, damage: int):
        assert damage >= 0

        self._health -= damage

    def is_dead(self):
        return self._health <= 0

    def draw_frame(self, surface: pygame.Surface):
        force = pymunk.Vec2d.from_polar(self._max_thrust if self.thrusting else 0.0, self.angle)
        self.force = force

        
        # RADAR


        radar_max_end = self.position + pymunk.Vec2d.from_polar(self.radar_range, self.angle)

        assert self.space is not None

        query_infos = self.space.segment_query(
            self.position,
            radar_max_end,
            0,
            pymunk.ShapeFilter()#SHAPE_FILTER_RADAR
        )

        
        found = None
        
        query_infos.sort(key=lambda q: q.alpha)
        for q in query_infos:
            if q.shape != self.poly:
                #print(q.alpha)
                found = q
                break
        

        dir = pymunk.Vec2d.from_polar(1.0, self.angle)

        hull_start = self.position + pymunk.Vec2d.from_polar(self.width * 0.5, self.angle)

        if found is None:
            self.radar_state.distance = self.radar_range
            pygame.draw.line(
                surface,
                self.color.lerp(pygame.Color("white"), 0.5),
                hull_start,
                radar_max_end,
                width=1
            )
            self.radar_state.freq = RadarFreq.NONE
        else:
            distance = self.radar_range * found.alpha
            self.radar_state.distance = distance
            target = found.shape

            if target.collision_type == CollisionLayer.SHIP.value:
                if self.radar_state.freq != RadarFreq.SHIP:
                    self.sound_detect_ship.play()
                self.radar_state.freq = RadarFreq.SHIP
            elif target.collision_type == CollisionLayer.PROJECTILE.value:
                self.radar_state.freq = RadarFreq.PROJECTILE
            elif target.collision_type == CollisionLayer.WALL.value:
                self.radar_state.freq = RadarFreq.WALL
            else:
                raise ValueError(target, target.collision_type, target.body)
            
            pygame.draw.line(
                surface,
                self.color,
                hull_start,
                self.position + distance * dir,
                width=4
            )
        
        

        facing_vec = pymunk.Vec2d.from_polar(1, self.angle)

        perp_vec = pymunk.Vec2d.from_polar(1, self.angle + math.pi/2)

        on = True

        EVERY = 10

        if self.take_damage_frames > 0:
            on = (self.take_damage_frames % EVERY) < EVERY/2
            self.take_damage_frames -= 1

        pygame.draw.polygon(surface, self.color, 
            [
                self.position + 0.5 * ( + perp_vec * self.height + facing_vec * self.width),
                self.position + 0.5 * ( - perp_vec * self.height + facing_vec * self.width),
                self.position + 0.5 * ( - perp_vec * self.height - facing_vec * self.width),
                self.position + 0.5 * ( + perp_vec * self.height - facing_vec * self.width)
            ],
            width = 0 if on else 2
        )

        if self.thrusting:

            rear_tip = self.position - pymunk.Vec2d.from_polar(self.width/2, self.angle)
            pygame.draw.polygon(surface, pygame.Color("orange"), [
                rear_tip,
                rear_tip - perp_vec * 8 - facing_vec * 7,
                rear_tip - facing_vec * 20,
                rear_tip + perp_vec * 8 - facing_vec * 7,
                rear_tip
            ]) 

            if self.sound_rocket_main.get_num_channels() <= 0:
                pass#self.sound_rocket_main.play(loops = -1)
        else:
            if self.sound_rocket_main.get_num_channels() > 0:
                self.sound_rocket_main.stop()

        if self.turn in [TurnDirection.Left, TurnDirection.Right]:
            self.torque = self._max_torque * (-1 if self.turn == TurnDirection.Left else 1)

        if self.shoot:
            self.shoot = False
            
            self.match.shoot_projectile(self)

        return True


class ProjectileGhost(DrawFrameHandled):
    def __init__(self, position: pymunk.Vec2d):
        self.position = position

        self.on = 0

        self.drawn_frames = 50

    def draw_frame(self, surface: pygame.Surface):
        if self.drawn_frames <= 0:
            return False

        EVERY = 10

        self.on += 1
        self.on %= EVERY

        if self.on < EVERY/2:
            pygame.draw.circle(surface, pygame.Color("white"), self.position, 8, width=1)
        
        self.drawn_frames -= 1

        return True


class Projectile(PolyBody, DrawFrameHandled):
    def __init__(self, space: pymunk.Space, position: pymunk.Vec2d, dir: float):
        super().__init__()
        
        self.poly = pymunk.Circle(self, 8)
        self.poly.mass = 5
        self.poly.color = pygame.Color("white")
        self.poly.collision_type = CollisionLayer.PROJECTILE.value
        self.poly.sensor = True
        self.poly.filter = SHAPE_FILTER_PROJECTILE

        self.position = position
        dir = dir

        offset = pymunk.Vec2d.from_polar(30, dir)

        extra_vel = pymunk.Vec2d.from_polar(30, dir)

        self.position += offset
        self.velocity += extra_vel
        space.add(self, self.poly)

    @classmethod
    def spawn(cls, space: pymunk.Space, from_: Ship):
        return cls(space, from_.position, from_.angle)
    
    def draw_frame(self, surface: pygame.Surface) -> bool:
        pygame.draw.circle(surface, pygame.Color("white"), self.position, 8)

        vec_backward = pymunk.Vec2d.from_polar(-16, self.angle)
        vec_normal = pymunk.Vec2d.from_polar(8, self.angle + math.pi/2)

        return not self.deleted
    
@dataclass
class InputState:
    thrust: bool = False
    turn_left: bool = False
    turn_right: bool = False
    shoot: bool = False

class Match:
    def __init__(self, surface: pygame.Surface):
        self.space = pymunk.Space()
        self.input_state = InputState()
        pymunk.pygame_util.positive_y_is_up = False

        self.draw_frame_handleds: list[DrawFrameHandled] = []

        self.map = Map(map, self.space)
        self.draw_frame_handleds.append(self.map)

        self.ship_a = Ship(self.space, default_ship_properties, self, pygame.Color("red"))
        self.draw_frame_handleds.append(self.ship_a)
        self.ship_a.position = self.map.spawn_a

        


        self.ship_b = Ship(self.space, default_ship_properties, self, pygame.Color("blue"))
        self.draw_frame_handleds.append(self.ship_b)
        self.ship_b.position = self.map.spawn_b
        self.ship_b.angle = math.pi


        self.draw_options = pymunk.pygame_util.DrawOptions(surface)

        self.space.on_collision(
            CollisionLayer.SHIP.value, CollisionLayer.PROJECTILE.value, begin=self._handle_ship_projectile_collision
        )
        self.space.on_collision(
            CollisionLayer.PROJECTILE.value, CollisionLayer.PROJECTILE.value, begin=self._handle_projectile_projectile_collision
        )
        self.space.on_collision(
            CollisionLayer.PROJECTILE.value, CollisionLayer.WALL.value, begin=self._handle_projectile_wall_collision
        )

        self.sound_projectile_explodes = pygame.mixer.Sound(SOUND_FILE_PROJECTILE_EXPLODE)

    def _handle_projectile_wall_collision(self, arbiter: pymunk.Arbiter, space: pymunk.Space, _):
        projectile = arbiter.bodies[0]
        

        ghost = ProjectileGhost(projectile.position)
        self.draw_frame_handleds.append(ghost)
        projectile.delete()
        self.sound_projectile_explodes.play()



    def _handle_projectile_projectile_collision(self, arbiter: pymunk.Arbiter, space: pymunk.Space, _):
        p1 = arbiter.bodies[0]
        
        p2 = arbiter.bodies[1]

        for p in arbiter.bodies:
            ghost = ProjectileGhost(p.position)
            self.draw_frame_handleds.append(ghost)
            p.delete()

        self.sound_projectile_explodes.play()

    def _handle_ship_projectile_collision(self, arbiter: pymunk.Arbiter, space: pymunk.Space, _):
        ship = arbiter.bodies[0]
        
        projectile = arbiter.bodies[1]

        ghost = ProjectileGhost(projectile.position)
        self.draw_frame_handleds.append(ghost)
        projectile.delete()

        self.sound_projectile_explodes.play()

        ship.start_taking_damage()


    def shoot_projectile(self, ship: Ship):
        p = Projectile.spawn(self.space, ship)
        self.draw_frame_handleds.append(p)

    def frame(self, dt, surface):
        for d in self.draw_frame_handleds:
            if not d.draw_frame(surface):
                self.draw_frame_handleds.remove(d)

        self.space.step(dt)
        #self.space.debug_draw(self.draw_options)

        #self.ship_a_driver.update(self.ship_a)
        

class Game:
    def __init__(self, fps=60, width=700, height=700):
        self.fps = fps
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()

        self.match = Match(self.screen)

    def frame(self):
        self.screen.fill(pygame.Color("black"))
        self.match.frame(1/self.fps, self.screen)
        pygame.display.flip()
        self.clock.tick(self.fps)

        set_shoot = False

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                return False
            elif event.type in [pygame.KEYDOWN, pygame.KEYUP]:
                if event.key == pygame.K_LEFT:
                    self.match.input_state.turn_left = event.type == pygame.KEYDOWN
                elif event.key == pygame.K_RIGHT:
                    self.match.input_state.turn_right = event.type == pygame.KEYDOWN
                elif event.key == pygame.K_SPACE:
                    set_shoot = event.type == pygame.KEYDOWN
                elif event.key == pygame.K_UP:
                    self.match.input_state.thrust = event.type == pygame.KEYDOWN

        self.match.input_state.shoot = set_shoot
            
        return True