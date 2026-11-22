"""Escape Dimension simulation. No graphics dependency: run tests headlessly."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from math import hypot, ceil, sin, cos, atan2, pi
import json
from pathlib import Path
from visuals import direction_index, torso_angle, deform_upper_point
from navigation import Navigator
from hazards import ObservationWindow,LaserBeam
from space import turn_point,turn_box,gravity_frame

WIDTH, HEIGHT = 1280, 800
LEFT, RIGHT, BOTTOM, TOP = 76.0, 1204.0, 154.0, 666.0
GRAVITY = 880.0
JUMP_HEIGHT = 50.0
JUMP_SPEED = (2*GRAVITY*JUMP_HEIGHT)**.5
ENEMY_JUMP_SPEED = 420.0
PLAYER_HALF = 22.0
MAGAZINE_SIZE = 6
MAX_AMMO = 42
RELOAD_DURATION = 1.25
DEATH_DURATION = .8
ENEMY_BULLET_SPEED = 320.0
KNIFE_SPEED = 420.0
BLAST_RADIUS = 148.0
MIN_LETHAL_FALL = 80.0
BOSS_KINDS = ('midboss', 'finalboss')


def clamp(value, low, high):
    return max(low, min(high, value))


def unit(dx, dy):
    length = hypot(dx, dy)
    return (dx / length, dy / length) if length > 0.00001 else (1.0, 0.0)


def segment_box(x1, y1, x2, y2, box, padding=0.0):
    """Time of first contact of a segment with an expanded AABB, or None."""
    left, bottom, right, top = box
    enter, leave = 0.0, 1.0
    for origin, delta, low, high in ((x1, x2-x1, left-padding, right+padding),
                                    (y1, y2-y1, bottom-padding, top+padding)):
        if abs(delta) < 1e-9:
            if origin < low or origin > high:
                return None
        else:
            a, b = (low-origin)/delta, (high-origin)/delta
            if a > b:
                a, b = b, a
            enter, leave = max(enter, a), min(leave, b)
            if enter > leave:
                return None
    return enter


@dataclass
class Actor:
    x: float
    y: float
    kind: str = "player"
    vy: float = 0.0
    alive: bool = True
    timer: float = 1.8
    aim_x: float = 0.0
    aim_y: float = 0.0
    winding: bool = False
    facing: int = 0
    moving: bool = False
    walk_distance: float = 0.0
    death_elapsed: float = 0.0
    route: list = field(default_factory=list)
    nav_left: float = 0.0
    nav_revision: int = -1
    nav_goal: tuple = (0.0,0.0)
    hp: int = 1
    max_hp: int = 1
    alerted: bool = True
    attack_cycle: int = 0
    phase: int = 1
    hurt_left: float = 0.0
    burst_left: int = 0
    burst_total: int = 0
    burst_delay: float = 0.0
    burst_angle: float = 0.0
    body_turn: int = 0

    def __post_init__(self):
        if self.kind in BOSS_KINDS and self.max_hp == 1:
            self.hp = self.max_hp = 18 if self.kind == 'midboss' else 36

    @property
    def half_width(self):
        return 32 if self.kind == 'finalboss' else 26 if self.kind == 'midboss' else 15

    @property
    def head_height(self):
        return 92 if self.kind == 'finalboss' else 74 if self.kind == 'midboss' else 48

    @property
    def box(self):
        # y is the foot anchor plus 22px. Include the sprite's head and torso.
        a,b,c,d=turn_box((-self.half_width,-22,self.half_width,self.head_height),-self.body_turn)
        return self.x+a,self.y+b,self.x+c,self.y+d


@dataclass
class Crate:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    held: bool = False
    hit_actors: set = field(default_factory=set)
    fall_distance: float = 0.0

    @property
    def box(self):
        return self.x-23, self.y-23, self.x+23, self.y+23


@dataclass
class ThrownKnife:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    fall_distance: float = 0.0
    hit_actors: set = field(default_factory=set)

    @property
    def box(self):return self.x-9,self.y-9,self.x+9,self.y+9


@dataclass
class Bullet:
    x: float
    y: float
    vx: float
    vy: float
    owner: str
    life: float = 3.0
    style: str = 'normal'


@dataclass
class Grenade:
    x: float
    y: float
    vx: float
    vy: float
    fuse: float = 1.6
    radius: float = BLAST_RADIUS
    age: float = 0.0
    flight_time: float = 1.0
    source: Actor | None = None
    redirected: bool = False
    redirect_count: int = 0


@dataclass
class Blast:
    x: float
    y: float
    radius: float
    life: float = .55


@dataclass
class Fragment:
    x: float
    y: float
    vx: float
    vy: float
    life: float = .8
    glass: bool = False


class Game:
    def __init__(self, level_path=None):
        level_path = level_path or Path(__file__).with_name("levels.json")
        self.levels = json.loads(Path(level_path).read_text(encoding="utf-8"))["rooms"]
        self.bounds = (LEFT, BOTTOM, RIGHT, TOP)
        self.state = "title"
        self.age = 20
        self.room_index = 0
        self.mode = 2
        self.awakened = False
        self.view_turn = 0
        self._local_depth = 0
        self._combat_bounds = None
        self.knife_owned = True
        self.entry_knife = True
        self.knives = []
        self.bomb_clock = 2.2
        self.player = Actor(160.0, self.bottom+PLAYER_HALF)
        self.enemies = []
        self.crates = []
        self.bullets = []
        self.grenades = []
        self.blasts = []
        self.fragments = []
        self.command_window = None
        self.lasers = []
        self.laser_clock = 1.0
        self.laser_cycle = 0
        self.obstacles = []
        self.reinforced = set()
        self.destroyed_cover = 0
        self.ammo_pickups = []
        self.effects = []
        self.events = []
        self.history = deque()
        self.selected = 0
        self.world_time = 0.0
        self.time_left = 0.0
        self.time_frozen = False
        self.magazine = MAGAZINE_SIZE
        self.reserve = MAX_AMMO-MAGAZINE_SIZE
        self.reload_left = 0.0
        self.shot_cooldown = 0.0
        self.shots = 0
        self.kills = 0
        self.total_deaths = 0
        self.streak = 0
        self.clear = False
        self.elapsed = 0.0
        self.hint = ""
        self.hint_left = 0.0
        self.last_age_cost = 0
        self.entry_ammo = (MAGAZINE_SIZE, MAX_AMMO-MAGAZINE_SIZE)
        self.grace = 0.0
        self._nav_signature = None
        self._navigator = None
        self._nav_cache = {}
        self._nav_revision = 0

    @property
    def room(self):
        return self.levels[self.room_index]

    @property
    def left(self): return self.bounds[0]

    @property
    def bottom(self): return self.bounds[1]

    @property
    def right(self): return self.bounds[2]

    @property
    def top(self): return self.bounds[3]

    def movement_bounds(self,actor=None):
        if self.command_window is not None and (actor is None or actor.kind=='player'):
            return self._combat_bounds
        return self.bounds

    def transform_scene(self,turns):
        """Temporary local gravity coordinates; never change authored level data."""
        point=lambda x,y:turn_point(x,y,turns)
        self.bounds=turn_box(self.bounds,turns)
        if self._combat_bounds:self._combat_bounds=turn_box(self._combat_bounds,turns)
        for a in [self.player]+self.enemies:
            a.x,a.y=point(a.x,a.y);a.aim_x,a.aim_y=point(a.aim_x,a.aim_y)
            a.facing=(a.facing-2*turns)%8;a.body_turn=(a.body_turn-turns)%4
            a.route=[point(*p) for p in a.route]
        for collection in (self.crates,self.knives,self.bullets,self.grenades,self.fragments):
            for obj in collection:
                obj.x,obj.y=point(obj.x,obj.y);obj.vx,obj.vy=point(obj.vx,obj.vy)
        for b in self.blasts:b.x,b.y=point(b.x,b.y)
        self.obstacles=[turn_box(r,turns) for r in self.obstacles]
        self.reinforced={turn_box(r,turns) for r in self.reinforced}
        self.ammo_pickups=[list(point(*p)) for p in self.ammo_pickups]
        self.effects=[[*point(x,y),life,kind] for x,y,life,kind in self.effects]
        self.history=deque((t,*point(x,y)) for t,x,y in self.history)
        if self.command_window:self.command_window.box=turn_box(self.command_window.box,turns)
        for laser in self.lasers:
            laser.x1,laser.y1=point(laser.x1,laser.y1);laser.x2,laser.y2=point(laser.x2,laser.y2)
        room=dict(self.room)
        for key in ('arena',):
            if key in room:room[key]=turn_box(room[key],turns)
        self.levels=list(self.levels);self.levels[self.room_index]=room
        self._nav_signature=None;self._nav_cache.clear()

    def rotate_view(self,step):
        if self.state!='playing' or self.mode!=4:return False
        if not self.awakened:
            self.message('6챕터를 클리어하면 공간 회전이 각성합니다');return False
        step=1 if step>0 else -1
        self.view_turn=(self.view_turn+step)%4
        for actor in [self.player]+self.enemies:actor.body_turn=self.view_turn
        for bomb in self.grenades:
            # Preserve the screen heading while the room turns around the bomb.
            bomb.vx,bomb.vy=turn_point(bomb.vx,bomb.vy,-step)
            bomb.redirected=True;bomb.redirect_count+=1
        for obj in self.crates+self.knives:obj.fall_distance=0
        self.stabilize_rotation()
        self.events.append('switch')
        self.message(f'각성 회전 {self.view_turn*90}° / 2D로 바꾸면 화면 아래로 낙하',3)
        return True

    @gravity_frame
    def stabilize_rotation(self):
        for actor in [self.player]+[e for e in self.enemies if e.kind!='finalboss']:
            self.move_actor(actor,0,0,0)
            for box in self.solids():
                if self.overlap(actor.box,box):
                    choices=[(abs(actor.box[2]-box[0]),box[0]-actor.half_width,actor.y),
                             (abs(box[2]-actor.box[0]),box[2]+actor.half_width,actor.y),
                             (abs(actor.box[3]-box[1]),actor.x,box[1]-actor.head_height),
                             (abs(box[3]-actor.box[1]),actor.x,box[3]+22)]
                    _,actor.x,actor.y=min(choices)
            actor.vy=0

    @property
    def speed(self):
        return 240.0 * (1.0 if self.age < 25 else .95 if self.age < 30 else .9 if self.age < 35 else .8)

    @property
    def precision(self):
        return .5 if self.age < 25 else .4 if self.age < 30 else .25 if self.age < 35 else .1

    @property
    def held(self):
        return next((c for c in self.crates if c.held), None)

    @property
    def total_ammo(self):
        return self.magazine+self.reserve

    @property
    def death_finished(self):
        return self.player.alive or self.player.death_elapsed >= DEATH_DURATION

    def aim_direction(self, aim, actor=None):
        actor = actor or self.player
        x,y=self.muzzle_position(aim,actor)
        return unit(aim[0]-x,aim[1]-y)

    def muzzle_position(self, aim, actor=None):
        actor=actor or self.player
        if actor.kind=='midboss':
            dx,dy=unit(aim[0]-actor.x,aim[1]-actor.y-28)
            return actor.x+dx*44,actor.y+28+dy*44
        if self.mode==2:
            angle=torso_angle(aim[0]-actor.x,aim[1]-actor.y-24)
            side=1 if aim[0]>=actor.x else -1
            x,y=deform_upper_point(side*27/84,15/84,angle,side)
            return actor.x+x*84,actor.y+18+y*84
        dx,dy=unit(aim[0]-actor.x,aim[1]-actor.y-24)
        return actor.x+dx*25,actor.y+24+dy*25

    @property
    def grounded(self):
        return self.actor_grounded(self.player)

    @gravity_frame
    def actor_grounded(self, actor):
        if self.mode != 2 or not actor.alive or actor.vy > 0:
            return False
        feet = actor.y-PLAYER_HALF
        if abs(feet-self.movement_bounds(actor)[1]) <= .5:
            return True
        return any(abs(feet-top) <= .5 and actor.x+actor.half_width > left
                   and actor.x-actor.half_width < right
                   for left,bottom,right,top in self.solids())

    @gravity_frame
    def jump(self):
        if self.state != 'playing' or not self.grounded:
            return False
        self.player.vy = JUMP_SPEED
        self.events.append('jump')
        return True

    def advance_deaths(self, dt):
        for actor in [self.player]+self.enemies:
            if not actor.alive:
                actor.death_elapsed = min(DEATH_DURATION+3, actor.death_elapsed+dt)

    def message(self, text, seconds=2.4):
        self.hint, self.hint_left = text, seconds

    def start(self):
        self.age, self.room_index, self.mode = 20, 0, 2
        self.awakened=False;self.knife_owned=True
        self.magazine, self.reserve = MAGAZINE_SIZE, MAX_AMMO-MAGAZINE_SIZE
        self.shots = self.kills = self.total_deaths = self.streak = 0
        self.elapsed = 0.0
        self.load_room()

    def load_room(self, retry=False):
        self.state = "playing"
        self.bounds = tuple(self.room.get("bounds", (LEFT, BOTTOM, RIGHT, TOP)))
        self.mode = self.room.get('start_mode',2)
        self.view_turn=0
        self.awakened=self.awakened or self.room_index>=6
        self.player = Actor(*self.room.get("spawn", [160, 176]))
        self.enemies = [Actor(float(e[0]), float(e[1]), e[2], timer=2.2+i*.45, facing=4, alerted=False)
                        for i, e in enumerate(self.room["enemies"])]
        self.crates = [Crate(float(x), float(y)) for x, y in self.room["crates"]]
        self.obstacles = [tuple(o) for o in self.room.get("obstacles", [])]
        self.reinforced = {tuple(o) for o in self.room.get('reinforced', [])}
        self.ammo_pickups = [list(p) for p in self.room.get("ammo", [])]
        spec=self.room.get('command_window')
        self.command_window=ObservationWindow(tuple(spec['box']),spec.get('hp',36),spec.get('hp',36)) if spec else None
        self._combat_bounds=tuple(self.room['arena'][:3])+ (min(self.room['arena'][3],self.command_window.box[1]),) if spec else None
        self.lasers=[];self.laser_clock=1.;self.laser_cycle=0
        self.bomb_clock=2.2
        self.knives=[]
        self.settle_initial_layout()
        if self.command_window:
            self.player.x,self.player.y=self.room['spawn']
            for e in self.enemies:
                if e.kind=='finalboss':
                    e.x=(self.command_window.box[0]+self.command_window.box[2])/2
                    e.y=self.command_window.box[1]+12
                    e.hp=e.max_hp=self.command_window.max_hp
        errors = self.layout_errors()
        if errors:
            raise ValueError(f"Invalid room {self.room_index+1}: " + "; ".join(errors))
        self.bullets, self.effects, self.events = [], [], []
        self.grenades, self.blasts, self.fragments = [], [], []
        self.destroyed_cover = 0
        self.history.clear()
        self.world_time = 0.0
        self.time_left = 0.0
        self.time_frozen = False
        self.reload_left = self.shot_cooldown = 0.0
        self.clear = False
        self.grace = 1.2
        self._nav_signature = None
        self._nav_cache = {}
        if retry:
            self.magazine, self.reserve = self.entry_ammo
            self.knife_owned=self.entry_knife
        else:
            self.entry_ammo = self.magazine, self.reserve
            self.entry_knife=self.knife_owned
        if not self.knife_owned:self.knives=[ThrownKnife(self.player.x+45,self.player.y)]
        self.history.append((0.0, self.player.x, self.player.y))
        self.message(self.room["hint"], 6.0)

    def settle_initial_layout(self):
        """Place objects on support without simulating damaging startup falls."""
        supports = list(self.obstacles)
        for crate in sorted(self.crates, key=lambda c: c.y):
            tops = [r[3] for r in supports
                    if crate.x+23 > r[0] and crate.x-23 < r[2]
                    and r[3] <= crate.y-23+.5]
            crate.y = max([self.bottom] + tops) + 23
            crate.vx = crate.vy = 0.0
            supports.append(crate.box)
        for actor in [self.player] + self.enemies:
            tops = [r[3] for r in supports
                    if actor.x+actor.half_width > r[0] and actor.x-actor.half_width < r[2]
                    and r[3] <= actor.y-PLAYER_HALF+.5]
            actor.y = max([self.bottom] + tops) + PLAYER_HALF
            actor.vy = 0.0

    def layout_errors(self):
        """Reject room entries inside cover instead of hiding authoring errors."""
        errors = []
        actors = [self.player] + self.enemies
        for index, actor in enumerate(actors):
            label = "player" if index == 0 else f"enemy {index}"
            x1,y1,x2,y2 = actor.box
            if x1 < self.left or x2 > self.right or y1 < self.bottom-.5 or y2 > self.top:
                errors.append(f"{label} outside room")
            if any(self.overlap(actor.box, rect) for rect in self.solids()):
                errors.append(f"{label} overlaps cover")
            if any(self.overlap(actor.box, other.box) for other in actors[:index]):
                errors.append(f"{label} overlaps another actor")
        for index, crate in enumerate(self.crates):
            x1,y1,x2,y2 = crate.box
            if x1 < self.left or x2 > self.right or y1 < self.bottom-.5 or y2 > self.top:
                errors.append(f"crate {index+1} outside room")
            if any(self.overlap(crate.box, rect) for rect in self.solids(skip=crate)):
                errors.append(f"crate {index+1} overlaps cover")
        return errors

    def next_room(self):
        if not self.clear or self.state != "playing":
            return False
        if self.mode == 4:
            self.leave_time()
            if self.state != "playing":
                return False
        self.streak = 0
        if self.room_index == len(self.levels)-1:
            self.state = "won"
            self.events.append("win")
        else:
            self.room_index += 1
            self.load_room()
        return True

    def age_up(self, amount):
        self.age += amount
        self.last_age_cost = amount
        if self.age >= 40:
            self.state = "over"
            self.time_frozen = False

    def die(self):
        if self.state != "playing":
            return
        cost = 2 ** self.streak
        # A death also ends an active 4D session, so both existing costs apply.
        if self.mode == 4:
            cost += 1
        self.streak += 1
        self.total_deaths += 1
        self.player.alive = False
        self.player.moving = False
        self.player.death_elapsed = 0.0
        self.time_frozen = False
        self.state = "dead"
        self.age_up(cost)
        self.events.append("death")

    def retry(self):
        if self.state == "dead":
            self.load_room(retry=True)
        elif self.state in ("over", "won"):
            self.start()

    def set_mode(self, mode):
        if self.state != "playing" or mode not in (2, 3, 4) or mode == self.mode:
            return False
        old_mode = self.mode
        if self.mode == 4:
            self.leave_time()
            if self.state != "playing":
                return False
        self.mode = mode
        for actor in [self.player]+self.enemies:actor.body_turn=self.view_turn
        for obj in self.crates+self.knives:obj.fall_distance=0
        for actor in self.enemies:
            actor.route.clear()
            actor.nav_left = 0
        if mode == 2:
            for actor in [self.player]+self.enemies:
                if actor.alive:
                    actor.facing = 4 if actor.facing in (3,4,5) else 0
        self.player.vy = 0.0
        if old_mode == 2 and mode in (3, 4):
            # Height velocity does not become motion across the reinterpreted floor.
            for obj in self.crates+self.knives:
                vx,vy=turn_point(obj.vx,obj.vy,self.view_turn)
                obj.vx,obj.vy=turn_point(vx,0,-self.view_turn)
            for enemy in self.enemies:
                enemy.vy = 0.0
        if mode == 4:
            self.time_left, self.selected = 10.0, 0
            self.message('각성: Z/X 공간 회전 / 휠 과거 선택 / Enter 이동' if self.awakened else '정지 중에도 10초 제한은 흐릅니다. 휠로 과거 선택, Enter로 이동',4.5)
        self.events.append("switch")
        return True

    def leave_time(self):
        if self.mode != 4:
            return
        self.mode = 3
        self.time_left = 0.0
        self.time_frozen = False
        self.age_up(1)
        self.events.append("switch")

    @gravity_frame
    def safe_position(self, x, y):
        left,bottom,right,top=self.movement_bounds(self.player)
        if not left+16 <= x <= right-16 or not bottom+PLAYER_HALF <= y <= top-48:
            return False
        box = (x-14, y-21, x+14, y+47)
        if any(self.overlap(box, r) for r in self.obstacles):
            return False
        if any(not c.held and self.overlap(box, c.box) for c in self.crates):
            return False
        if any(laser.active and self.overlap(box,laser.box) for laser in self.lasers):return False
        return not any(e.alive and (self.overlap(box,e.box) or hypot(x-e.x,y-e.y)<38) for e in self.enemies)

    def rewind_points(self):
        if not self.history:
            return []
        points = []
        for index in range(1, int(4.0/self.precision+.001)+1):
            ago = round(index*self.precision, 3)
            target_time = self.world_time-ago
            if target_time < self.history[0][0]-.03:
                continue
            record = min(self.history, key=lambda h: abs(h[0]-target_time))
            if not any(hypot(p[1]-record[1], p[2]-record[2]) < 4 for p in points):
                points.append((ago, record[1], record[2], self.safe_position(record[1], record[2])))
        return points

    def select_rewind(self, delta=0, index=None):
        points = self.rewind_points()
        if points:
            self.selected = int(clamp(index if index is not None else self.selected+delta, 0, len(points)-1))

    def rewind(self):
        points = self.rewind_points()
        if self.mode != 4 or not points or self.state != "playing":
            return False
        self.selected = int(clamp(self.selected, 0, len(points)-1))
        ago, x, y, safe = points[self.selected]
        if not safe:
            self.message("사물이 겹친 위치입니다. 다른 잔상을 선택하세요")
            return False
        self.player.x, self.player.y, self.player.vy = x, y, 0.0
        if self.held:
            ox,oy=turn_point(0,49,-self.view_turn)
            self.held.x, self.held.y = x+ox, y+oy
        self.leave_time()
        self.events.append("rewind")
        self.message(f"{ago:g}초 전 위치로 이동 / 나이 +1")
        return True

    @gravity_frame
    def pickup(self):
        if self.state != "playing":
            return False
        if self.clear and self.player.x > self.right-110:
            return self.next_room()
        nearby_knives=[k for k in self.knives if hypot(k.x-self.player.x,k.y-self.player.y)<104]
        if not self.knife_owned and nearby_knives:
            self.knives.remove(min(nearby_knives,key=lambda k:hypot(k.x-self.player.x,k.y-self.player.y)))
            self.knife_owned=True;self.events.append('pickup');self.message('칼 회수 / F 투척');return True
        if self.held:
            self.message("Q로 물체를 던질 수 있습니다")
            return False
        near = [c for c in self.crates if hypot(c.x-self.player.x, c.y-self.player.y) < 104]
        if not near:
            self.message('가까운 상자 또는 던진 칼에 다가가 E를 누르세요')
            return False
        crate = min(near, key=lambda c: hypot(c.x-self.player.x, c.y-self.player.y))
        crate.held, crate.vx, crate.vy = True, 0.0, 0.0
        crate.hit_actors.clear()
        crate.fall_distance=0
        self.events.append("pickup")
        return True

    @gravity_frame
    def throw(self, aim):
        crate = self.held
        if not crate or self.state != "playing":
            return False
        dx, dy = self.aim_direction(aim)
        crate.held = False
        crate.x = clamp(self.player.x+dx*48, self.left+24, self.right-24)
        crate.y = clamp(self.player.y+dy*48, self.bottom+24, self.top-24)
        crate.vx, crate.vy = dx*480, dy*480+(100 if self.mode == 2 else 0)
        crate.fall_distance=0
        self.events.append("throw")
        return True

    @gravity_frame
    def throw_knife(self,aim):
        if self.state!='playing' or not self.knife_owned:return False
        dx,dy=self.aim_direction(aim)
        self.knives.append(ThrownKnife(clamp(self.player.x+dx*35,self.left+10,self.right-10),
                           clamp(self.player.y+24+dy*35,self.bottom+10,self.top-10),dx*530,dy*530))
        self.knife_owned=False;self.events.append('throw')
        self.message('칼 투척 / 2D에서 80px 이상 낙하해야 피해 / E 회수',3)
        return True

    def reload(self):
        if self.state == "playing" and self.magazine < MAGAZINE_SIZE and self.reserve and self.reload_left <= 0:
            self.reload_left = RELOAD_DURATION
            self.events.append("reload")
            return True
        return False

    @gravity_frame
    def shoot(self, aim):
        if self.state != "playing" or self.reload_left > 0 or self.shot_cooldown > 0:
            return False
        if self.magazine <= 0:
            self.message("탄창이 비었습니다. R로 장전하세요", 1.0)
            return False
        muzzle_x,muzzle_y = self.muzzle_position(aim)
        dx, dy = self.aim_direction(aim)
        self.player.facing = direction_index(aim[0]-self.player.x,aim[1]-self.player.y-24,self.mode)
        self.bullets.append(Bullet(muzzle_x,muzzle_y,dx*850,dy*850,"player"))
        self.shot_cooldown, self.magazine = .22, self.magazine-1
        self.shots += 1
        self.events.append("shot")
        self.effects.append([muzzle_x+dx*4,muzzle_y+dy*4,.1,"flash"])
        return True

    @staticmethod
    def overlap(a, b):
        return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]

    def solids(self, skip=None):
        return self.obstacles + [c.box for c in self.crates if not c.held and c is not skip]

    def move_actor(self, actor, dx, dy, dt, gravity=False):
        before_x,before_y = actor.x,actor.y
        left,bottom,right,top=self.movement_bounds(actor)
        actor.x += dx
        actor.x = clamp(actor.x, left+actor.half_width+1, right-actor.half_width-1)
        for box in self.solids():
            if self.overlap(actor.box, box):
                if dx > 0: actor.x = box[0]-actor.half_width
                elif dx < 0: actor.x = box[2]+actor.half_width
        old_y = actor.y
        if gravity:
            dy = actor.vy*dt-.5*GRAVITY*dt*dt
            actor.vy -= GRAVITY*dt
        actor.y = clamp(actor.y+dy, bottom+PLAYER_HALF, top-actor.head_height)
        if actor.y in (bottom+PLAYER_HALF, top-actor.head_height):
            actor.vy = 0
        for box in self.solids():
            if self.overlap(actor.box, box):
                if dy < 0 and (not gravity or old_y-PLAYER_HALF >= box[3]-.5):
                    actor.y, actor.vy = box[3]+PLAYER_HALF, 0
                elif dy > 0:
                    actor.y, actor.vy = box[1]-actor.head_height, 0
                elif not gravity and abs(dx) < .001:
                    actor.y = old_y
        distance = hypot(actor.x-before_x, 0 if gravity else actor.y-before_y)
        actor.moving = distance > .001
        if actor.moving:
            actor.walk_distance += distance

    def update_crates(self, dt):
        """Crates and the single knife hurt only after real gravity-driven travel."""
        for c in self.crates+self.knives:
            knife=isinstance(c,ThrownKnife)
            half=9 if knife else 23
            if not knife and c.held:
                c.x,c.y=self.player.x,min(self.top-half,self.player.y+49)
                c.fall_distance=0
                continue
            old_x,old_y=c.x,c.y
            if self.mode==2:c.vy-=GRAVITY*dt
            else:
                c.vx*=max(0,1-1.5*dt);c.vy*=max(0,1-1.5*dt)
            previous_fall=c.fall_distance
            c.x+=c.vx*dt;c.y+=c.vy*dt
            c.fall_distance=c.fall_distance+max(0,old_y-c.y) if self.mode==2 and c.vy<0 else 0
            solid_t=min((t for r in self.solids(skip=c)
                         if (t:=segment_box(old_x,old_y,c.x,c.y,r,half)) is not None),default=2.)
            if self.mode==2 and c.vy<0:
                for enemy in self.enemies:
                    t=segment_box(old_x,old_y,c.x,c.y,enemy.box,half)
                    if enemy.alive and t is not None and t<=solid_t and id(enemy) not in c.hit_actors:
                        c.hit_actors.add(id(enemy))
                        distance_at_contact=previous_fall+max(0,old_y-c.y)*t
                        if distance_at_contact>=MIN_LETHAL_FALL:
                            self.damage_enemy(enemy,6 if enemy.kind in BOSS_KINDS else 1)
                            self.effects.append([c.x,c.y,.3,'slash' if knife else 'hit'])
            landed=False
            if c.y<self.bottom+half:
                c.y,c.vy,c.vx=self.bottom+half,0.,c.vx*.72;landed=True
            if c.x<self.left+half or c.x>self.right-half:
                c.x,c.vx=clamp(c.x,self.left+half,self.right-half),-c.vx*.3
            if c.y>self.top-half:c.y,c.vy=self.top-half,0;landed=True
            for box in self.solids(skip=c):
                if self.overlap(c.box,box):
                    if old_y-half>=box[3]-.5 and c.vy<=0:
                        c.y,c.vy,c.vx=box[3]+half,0,c.vx*.8;landed=True
                    elif old_y+half<=box[1]+.5 and c.vy>0:
                        c.y,c.vy=box[1]-half,0;landed=True
                    elif old_x<c.x:c.x,c.vx=box[0]-half,0
                    elif old_x>c.x:c.x,c.vx=box[2]+half,0
            if landed:c.fall_distance=0

    def kill(self, enemy):
        if enemy.alive:
            if enemy.kind=='finalboss' and self.command_window:
                self.command_window.hp=0
                self.lasers.clear()
            enemy.hp = 0
            enemy.alive = False
            enemy.moving = False
            enemy.death_elapsed = 0.0
            self.kills += 1
            self.effects.append([enemy.x, enemy.y, .45, "hit"])
            self.events.append("hit")

    def damage_enemy(self, enemy, amount=1):
        if not enemy.alive:
            return
        if enemy.kind=='finalboss' and self.command_window:return
        enemy.alerted = True
        enemy.hp = max(0, enemy.hp-amount)
        enemy.hurt_left = .18
        if not enemy.hp:
            self.kill(enemy)
        else:
            self.effects.append([enemy.x, enemy.y+25, .18, 'hit'])
            self.events.append('hit')

    def damage_window(self, amount=1, impact=None):
        window=self.command_window
        if window is None or window.hp<=0:return
        window.hp=max(0,window.hp-amount);window.hit_flash=.18
        boss=next((e for e in self.enemies if e.kind=='finalboss'),None)
        if boss:boss.hp=window.hp
        x,y=(window.box[0]+window.box[2])/2,(window.box[1]+window.box[3])/2
        self.effects.append([*(impact or (x,y)),.18,'glass'])
        self.events.append('glass_hit')
        if not window.hp:
            if boss:self.kill(boss)
            self.lasers.clear()
            self.grenades.clear()
            self.events.append('glass_break')
            for i in range(22):
                angle=i*2.4
                self.fragments.append(Fragment(x+(i%7-3)*43,y,cos(angle)*150,-70-abs(sin(angle))*180,1.1,True))
            self.message('관제창 파괴! 사령관 제압 / 레이저 정지',6)

    def spawn_laser_wave(self):
        left,bottom,right,top=self.movement_bounds(self.player)
        side=('left','top','right','bottom')[self.laser_cycle%4]
        phase=next(e for e in self.enemies if e.kind=='finalboss').phase
        # Dense staggered lanes retain gaps wider than the player's body.
        target_x=clamp(self.player.x,left+70,right-70)
        target_y=clamp(self.player.y+20,bottom+65,top-65)
        xs=[target_x]
        for offset in (-230,230,-430,430):
            value=clamp(target_x+offset,left+45,right-45)
            if all(abs(value-v)>100 for v in xs):xs.append(value)
        ys=[target_y]
        for value in (bottom+65,top-65,(bottom+top)/2):
            if all(abs(value-v)>112 for v in ys):ys.append(value)
        if phase==3:ys=[bottom+65,(bottom+top)/2,top-65]
        vertical=(2,3,4)[phase-1];horizontal=(1,2,3)[phase-1]
        # Narrow rotated local arenas still have deliberately avoidable lanes.
        xs=xs[:vertical];ys=ys[:horizontal]
        for i,x in enumerate(xs):
            direction='top' if i%2==0 else 'bottom'
            args=(x,top-3,x,bottom+3) if direction=='top' else (x,bottom+3,x,top-3)
            self.lasers.append(LaserBeam(*args,direction,warning=(.9,.85,.8)[phase-1],duration=.48))
        for i,y in enumerate(ys):
            direction=side if side in ('left','right') and i==0 else ('left' if i%2==0 else 'right')
            args=(left+3,y,right-3,y) if direction=='left' else (right-3,y,left+3,y)
            self.lasers.append(LaserBeam(*args,direction,warning=(.9,.85,.8)[phase-1],duration=.48))
        self.laser_cycle+=1
        self.laser_clock=(1.55,1.4,1.3)[phase-1]
        self.events.append('laser_charge')

    def update_command_stage(self,dt):
        window=self.command_window
        if window is None:return
        window.hit_flash=max(0,window.hit_flash-dt)
        boss=next((e for e in self.enemies if e.kind=='finalboss'),None)
        if window.hp<=0 or boss is None or not boss.alive:
            self.lasers.clear();return
        boss.phase=1+(window.hp<=window.max_hp*2/3)+(window.hp<=window.max_hp/3)
        if self.grace<=0:
            self.laser_clock-=dt;self.bomb_clock-=dt
            if self.laser_clock<=0:self.spawn_laser_wave()
            if self.bomb_clock<=0:
                self.launch_grenade(boss,(self.player.x,self.player.y+18))
                if boss.phase==3:
                    self.launch_grenade(boss,(clamp(self.player.x+160,*self.movement_bounds()[::2]),self.player.y+18))
                self.bomb_clock=(2.7,2.3,1.9)[boss.phase-1]
        for laser in self.lasers:
            was_active=laser.active
            laser.age+=dt
            if laser.active and not was_active:self.events.append('laser_fire')
            if self.grace<=0 and laser.active and self.overlap(self.player.box,laser.box):self.die()
        self.lasers=[laser for laser in self.lasers if not laser.finished]

    @staticmethod
    def distance_to_rect(x, y, rect):
        return hypot(x-clamp(x,rect[0],rect[2]),y-clamp(y,rect[1],rect[3]))

    def explode(self, grenade):
        """Near-cover blast tests use the nearest edge, not the wall centre."""
        x,y,radius = grenade.x,grenade.y,grenade.radius
        if grenade.redirected and self.command_window and self.distance_to_rect(x,y,self.command_window.box)<=radius*.7:
            self.damage_window(6,(x,y))
        removed=[r for r in self.obstacles if r not in self.reinforced
                 and self.distance_to_rect(x,y,r)<=radius]
        self.obstacles=[r for r in self.obstacles if r not in removed]
        broken=[c for c in self.crates if self.distance_to_rect(x,y,c.box)<=radius]
        self.crates=[c for c in self.crates if c not in broken]
        self.destroyed_cover += len(removed)+len(broken)
        if removed or broken:
            self._nav_signature = None
            self._nav_cache.clear()
            for e in self.enemies:
                e.route.clear();e.nav_left=0
            for i,r in enumerate(removed+[c.box for c in broken]):
                for j in range(5):
                    angle=(i*1.1+j*1.7)% (2*pi)
                    self.fragments.append(Fragment((r[0]+r[2])/2,(r[1]+r[3])/2,
                                                   cos(angle)*(95+j*22),sin(angle)*160+80))
        # The owner is immune to its own blast; other enemies can be caught in it.
        for enemy in self.enemies:
            if enemy.alive and enemy is not grenade.source and self.distance_to_rect(x,y,enemy.box)<=radius*.7:
                self.damage_enemy(enemy,4 if enemy.kind in BOSS_KINDS else 1)
        if self.grace<=0 and self.distance_to_rect(x,y,self.player.box)<=radius*.7:
            self.die()
        self.blasts.append(Blast(x,y,radius))
        self.events.append('explosion')

    def launch_grenade(self, enemy, target=None):
        tx,ty=target or (enemy.aim_x,enemy.aim_y)
        sx,sy=self.muzzle_position((tx,ty),enemy)
        flight=clamp(hypot(tx-sx,ty-sy)/470,.55,1.3)
        vx,vy=(tx-sx)/flight,(ty-sy)/flight
        if self.mode==2:vy+=.5*GRAVITY*.75*flight
        self.grenades.append(Grenade(sx,sy,vx,vy,flight+.45,BLAST_RADIUS,
                                     flight_time=flight,source=enemy))
        self.events.append('grenade')

    def update_grenades(self, dt):
        kept=[]
        for grenade in list(self.grenades):
            grenade.age+=dt;grenade.fuse-=dt
            if grenade.age>=grenade.flight_time and self.mode!=2:
                grenade.vx=grenade.vy=0
            nx,ny=grenade.x+grenade.vx*dt,grenade.y+grenade.vy*dt
            if self.mode==2:
                ny-=.5*GRAVITY*.75*dt*dt
                grenade.vy-=GRAVITY*.75*dt
            contact=min((t for r in self.solids()
                         if (t:=segment_box(grenade.x,grenade.y,nx,ny,r,7)) is not None),default=2.)
            window_t=segment_box(grenade.x,grenade.y,nx,ny,self.command_window.box,7) if self.command_window and grenade.redirected else None
            if window_t is not None and window_t<=contact:contact=window_t
            edge=not self.left+7<nx<self.right-7 or not self.bottom+7<ny<self.top-7
            if contact<=1:
                grenade.x+=(nx-grenade.x)*contact;grenade.y+=(ny-grenade.y)*contact
            else:grenade.x,grenade.y=nx,ny
            if contact<=1 or edge or grenade.fuse<=0:
                grenade.x=clamp(grenade.x,self.left+7,self.right-7)
                grenade.y=clamp(grenade.y,self.bottom+7,self.top-7)
                self.explode(grenade)
                if self.command_window and self.command_window.hp<=0:
                    kept=[];break
            else:kept.append(grenade)
        self.grenades=kept
        for b in self.blasts:b.life-=dt
        self.blasts=[b for b in self.blasts if b.life>0]
        for p in self.fragments:
            p.life-=dt;p.x+=p.vx*dt;p.y+=p.vy*dt;p.vy-=460*dt
        self.fragments=[p for p in self.fragments if p.life>0]

    def blocked(self, x1, y1, x2, y2):
        return any(segment_box(x1, y1, x2, y2, b) is not None for b in self.solids())

    def chase(self, enemy, speed, dt, target=None):
        """Use the same collision body as the player; never move through cover."""
        before=enemy.x,enemy.y
        if self.mode == 2:
            target_x=(target or (self.player.x,self.player.y))[0]
            if self.actor_grounded(enemy):
                feet=enemy.y-PLAYER_HALF
                support=next((r for r in self.solids() if abs(r[3]-feet)<.5
                              and r[0]-15<enemy.x<r[2]+15),None)
                if support and self.player.y < enemy.y-45 and support[0]-15<target_x<support[2]+15:
                    # Leave a ledge via its nearer end instead of pacing above the player.
                    edges=(support[0]-18,support[2]+18)
                    target_x=min(edges,key=lambda x:abs(enemy.x-x)+abs(self.player.x-x))
                direction=1 if target_x>enemy.x else -1
                lookahead=max(32,speed*.12)
                x1,x2=sorted((enemy.x+direction*15,enemy.x+direction*lookahead))
                blockers=[r for r in self.solids() if r[0]<x2 and r[2]>x1
                          and r[1]<enemy.y+48 and r[3]>feet+.5]
                max_height=ENEMY_JUMP_SPEED**2/(2*GRAVITY)-5
                jumpable=blockers and all(r[3]-feet<=max_height for r in blockers)
                overhead=any(r[0]<enemy.x+15 and r[2]>enemy.x-15
                             and enemy.y+48<=r[1]<enemy.y+48+max_height for r in self.solids())
                if jumpable and not overhead:
                    enemy.vy=ENEMY_JUMP_SPEED
            dx=clamp(target_x-enemy.x,-speed*dt,speed*dt)
            self.move_actor(enemy,dx,0,dt,True)
        else:
            solids=self.solids()
            signature=tuple(tuple(round(v,1) for v in rect) for rect in solids)
            if signature!=self._nav_signature:
                self._nav_signature=signature
                self._nav_revision+=1
                self._nav_cache.clear()
            shape=(enemy.half_width,enemy.head_height)
            if shape not in self._nav_cache:
                self._nav_cache[shape]=Navigator(solids,
                    (self.left+enemy.half_width+1,self.bottom+22,self.right-enemy.half_width-1,self.top-enemy.head_height),
                    segment_box,enemy.half_width,enemy.head_height)
            self._navigator=self._nav_cache[shape]
            enemy.nav_left-=dt
            goal=target or (self.player.x,self.player.y)
            if (enemy.nav_left<=0 or enemy.nav_revision!=self._nav_revision
                    or hypot(goal[0]-enemy.nav_goal[0],goal[1]-enemy.nav_goal[1])>60):
                enemy.route=self._navigator.route((enemy.x,enemy.y),goal)
                enemy.nav_goal=goal;enemy.nav_left=.22;enemy.nav_revision=self._nav_revision
            while enemy.route and hypot(enemy.route[0][0]-enemy.x,enemy.route[0][1]-enemy.y)<.4:
                enemy.route.pop(0)
            if enemy.route:
                x,y=enemy.route[0];dx,dy=unit(x-enemy.x,y-enemy.y)
                distance=min(speed*dt,hypot(x-enemy.x,y-enemy.y))
                self.move_actor(enemy,dx*distance,dy*distance,dt)
            else:
                self.move_actor(enemy,0,0,dt)
        if enemy.moving and enemy.kind in ('hunter','knife'):
            enemy.facing=direction_index(enemy.x-before[0],enemy.y-before[1],self.mode)

    def update_enemies(self, dt):
        for e in self.enemies:
            if not e.alive:
                continue
            if e.kind=='finalboss' and self.command_window:continue
            e.hurt_left=max(0,e.hurt_left-dt)
            dx, dy = unit(self.player.x-e.x, self.player.y-e.y)
            e.facing = direction_index(dx,dy,self.mode)
            distance=hypot(self.player.x-e.x,self.player.y-e.y)
            if not e.alerted:
                e.alerted=distance < (960 if e.kind in BOSS_KINDS else 820)
                if not e.alerted:
                    self.move_actor(e,0,0,dt,self.mode==2)
                    continue
            if e.kind in BOSS_KINDS:
                self.update_boss(e,dt,distance)
                if self.grace<=0 and self.overlap(self.player.box,e.box):self.die()
                if self.state!='playing':return
                continue
            if e.kind=='grenadier':
                self.update_grenadier(e,dt,distance)
                if self.grace<=0 and self.overlap(self.player.box,e.box):self.die()
                if self.state!='playing':return
                continue
            sight=not self.blocked(e.x,e.y+24,self.player.x,self.player.y+24)
            pursuing=e.kind in ('hunter','knife') or not sight or distance>480
            if self.grace<=0 and pursuing:
                speed=(min(560,KNIFE_SPEED+self.room_index*20) if e.kind=='knife'
                       else 76+self.room_index*8 if e.kind=='hunter' else 110+self.room_index*8)
                self.chase(e,speed,dt)
            else:
                self.move_actor(e,0,0,dt,self.mode==2)
            if e.kind == 'sentry':
                if self.grace <= 0 and not self.clear:
                    e.timer -= dt
                    if e.timer <= .8 and not e.winding:
                        e.winding = True
                    if e.winding and e.timer > .15:
                        e.aim_x, e.aim_y = self.player.x, self.player.y+24
                    if e.timer <= 0:
                        if not self.blocked(e.x, e.y+24, e.aim_x, e.aim_y):
                            ax, ay = self.aim_direction((e.aim_x,e.aim_y),e)
                            muzzle_x,muzzle_y=self.muzzle_position((e.aim_x,e.aim_y),e)
                            speed = min(520,ENEMY_BULLET_SPEED+self.room_index*25)
                            self.bullets.append(Bullet(muzzle_x,muzzle_y,ax*speed,ay*speed,"enemy",6.0))
                            self.events.append("enemy_shot")
                        e.winding = False
                        e.timer = max(1.65,2.5-self.room_index*.1)
            if (e.kind=='knife' and self.grace<=0
                    and hypot(self.player.x-e.x,self.player.y-e.y)<48
                    and not self.blocked(e.x,e.y+24,self.player.x,self.player.y+24)):
                self.effects.append([e.x,e.y+20,.22,'slash'])
                self.die()
                return
            if self.grace<=0 and self.overlap(self.player.box,e.box):
                self.die()
                return

    def update_grenadier(self, e, dt, distance):
        if self.grace>0:
            self.move_actor(e,0,0,dt,self.mode==2)
            return
        if not e.winding and distance>650:
            self.chase(e,115,dt)
        elif not e.winding and distance<230 and self.mode!=2:
            dx,dy=unit(e.x-self.player.x,e.y-self.player.y)
            target=(clamp(e.x+dx*200,self.left+18,self.right-18),
                    clamp(e.y+dy*200,self.bottom+22,self.top-48))
            self.chase(e,105,dt,target)
        else:self.move_actor(e,0,0,dt,self.mode==2)
        e.timer-=dt
        if e.timer<=1.1:
            e.winding=True
            if e.timer>.38:e.aim_x,e.aim_y=self.player.x,self.player.y+20
        if e.timer<=0:
            self.launch_grenade(e)
            e.winding=False;e.timer=3.3

    def update_boss(self, e, dt, distance):
        """Elite soldier: locked aim, short machine-gun burst, then reload."""
        if e.kind!='midboss':return
        phase=1+(e.hp<=e.max_hp*.5)
        if e.phase!=phase:
            e.phase=phase
            self.message('엘리트 기관총 사수 / 연사 강화',3)
        if self.grace>0:
            self.move_actor(e,0,0,dt,self.mode==2)
            return
        if e.burst_left<=0:
            if not e.winding and distance>560:self.chase(e,115,dt)
            else:self.move_actor(e,0,0,dt,self.mode==2)
            e.timer-=dt
            if e.timer<=.95:
                e.winding=True
                if e.timer>.3:e.aim_x,e.aim_y=self.player.x,self.player.y+24
            if e.timer>0:return
            e.burst_total=e.burst_left=12 if phase==1 else 18
            e.burst_delay=0
            e.burst_angle=atan2(e.aim_y-e.y-24,e.aim_x-e.x)
            e.winding=False
        else:self.move_actor(e,0,0,dt,self.mode==2)
        e.facing=direction_index(cos(e.burst_angle),sin(e.burst_angle),self.mode)
        e.burst_delay-=dt
        while e.burst_left>0 and e.burst_delay<=0:
            index=e.burst_total-e.burst_left
            angle=e.burst_angle+sin((index+1)*1.83)*(.028 if phase==1 else .045)
            sx,sy=self.muzzle_position((e.x+cos(angle)*400,e.y+24+sin(angle)*400),e)
            speed=460+phase*20
            self.bullets.append(Bullet(sx,sy,cos(angle)*speed,sin(angle)*speed,'enemy',6,'machinegun'))
            self.effects.append([sx,sy,.07,'flash'])
            self.events.append('machinegun')
            e.burst_left-=1;e.burst_delay+=.085 if phase==1 else .07
        if e.burst_left<=0:
            e.attack_cycle+=1;e.timer=2.05 if phase==1 else 1.7

    def update_bullets(self, dt):
        kept = []
        for b in self.bullets:
            nx, ny = b.x+b.vx*dt, b.y+b.vy*dt
            best_t, hit_actor, hit_window = 2.0, None, False
            for rect in self.solids():
                t = segment_box(b.x, b.y, nx, ny, rect, 2)
                if t is not None and t < best_t:
                    best_t, hit_actor = t, None
            if b.owner=='player' and self.command_window and self.command_window.hp>0:
                t=segment_box(b.x,b.y,nx,ny,self.command_window.box,2)
                if t is not None and t<=best_t:best_t,hit_window=t,True
            targets = [e for e in self.enemies if e.alive and not (e.kind=='finalboss' and self.command_window)] if b.owner == "player" else [self.player]
            for actor in targets:
                t = segment_box(b.x, b.y, nx, ny, actor.box, 2)
                if t is not None and t < best_t:
                    best_t, hit_actor, hit_window = t, actor, False
            if best_t <= 1:
                if hit_window:
                    self.damage_window(impact=(b.x+(nx-b.x)*best_t,b.y+(ny-b.y)*best_t))
                elif hit_actor is self.player:
                    if self.grace <= 0:
                        self.die()
                elif hit_actor is not None:
                    self.damage_enemy(hit_actor)
                self.effects.append([b.x+(nx-b.x)*best_t, b.y+(ny-b.y)*best_t, .2, "spark"])
                continue
            b.x, b.y, b.life = nx, ny, b.life-dt
            if b.life > 0 and self.left-10 < nx < self.right+10 and self.bottom-10 < ny < self.top+10:
                kept.append(b)
        self.bullets = kept

    @gravity_frame
    def tick(self, dt, move=(0, 0), aim=(900, 300), firing=False):
        dt = clamp(dt, 0, .05)
        if self.state in ('dead','over'):
            self.advance_deaths(dt)
            return
        if self.state != "playing":
            return
        self.player.facing = direction_index(aim[0]-self.player.x,aim[1]-self.player.y-24,self.mode)
        self.elapsed += dt
        self.hint_left = max(0, self.hint_left-dt)
        self.shot_cooldown = max(0, self.shot_cooldown-dt)
        if self.mode == 4:
            self.time_left -= dt
            if self.time_left <= 0:
                self.leave_time()
                if self.state != "playing":
                    return
        mx, my = move
        if self.mode!=2 and self.view_turn and not self._local_depth:mx,my=turn_point(mx,my,-self.view_turn)
        if self.mode == 2:
            my = 0
        length = hypot(mx, my)
        if length > 1:
            mx, my = mx/length, my/length
        before = self.player.x, self.player.y
        self.move_actor(self.player, mx*self.speed*dt, my*self.speed*dt, dt, self.mode == 2)
        moving = hypot(self.player.x-before[0], self.player.y-before[1]) > .01
        self.time_frozen = self.mode == 4 and not moving
        world_dt = 0.0 if self.time_frozen else dt
        self.effects = [[x,y,life-world_dt,kind] for x,y,life,kind in self.effects if life>world_dt]
        if self.held:
            ox,oy=turn_point(0,49,-self.view_turn if not self._local_depth else 0)
            self.held.x,self.held.y=self.player.x+ox,self.player.y+oy
        if self.reload_left > 0:
            self.reload_left -= world_dt
            if self.reload_left <= 0:
                take = min(MAGAZINE_SIZE-self.magazine, self.reserve)
                self.magazine, self.reserve = self.magazine+take, self.reserve-take
        if firing:
            self.shoot(aim)
        if world_dt > 0:
            self.advance_deaths(world_dt)
            self.world_time += world_dt
            self.grace = max(0, self.grace-world_dt)
            self.update_crates(world_dt)
            self.update_enemies(world_dt)
            if self.state != "playing":
                return
            self.update_bullets(world_dt)
            if self.state != "playing":
                return
            self.update_grenades(world_dt)
            if self.state != 'playing':return
            self.update_command_stage(world_dt)
            if self.state != 'playing':return
            if not self.history or self.world_time-self.history[-1][0] >= .045:
                self.history.append((self.world_time, self.player.x, self.player.y))
            while len(self.history) > 1 and self.history[0][0] < self.world_time-4.1:
                self.history.popleft()
            for pickup in list(self.ammo_pickups):
                if hypot(self.player.x-pickup[0], self.player.y-pickup[1]) < 46:
                    amount = min(28, max(0, MAX_AMMO-self.total_ammo))
                    if amount:
                        self.reserve += amount
                        self.ammo_pickups.remove(pickup)
                        self.events.append("pickup")
                        self.message(f"예비 탄약 +{amount} / 최대 합계 {MAX_AMMO}발")
                    elif self.hint_left <= 0:
                        self.message(f"탄약이 가득 찼습니다 / 합계 {MAX_AMMO}발")
        if not any(e.alive for e in self.enemies) and not self.clear:
            self.clear = True
            if self.room_index==5 and not self.awakened:
                self.awakened=True;self.events.append('rewind')
            self.message('각성 해금! 4D에서 Z/X 회전 / Enter 다음 챕터' if self.room_index==5 else '관제창 파괴! 레이저 정지 / Enter 탈출' if self.command_window else '챕터 클리어! Enter 또는 오른쪽 출구로 다음 챕터',30)
            self.events.append("clear")
        if self.clear and self.player.x >= self.right-29:
            self.next_room()
