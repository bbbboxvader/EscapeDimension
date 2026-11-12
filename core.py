"""Escape Dimension simulation. No graphics dependency: run tests headlessly."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import hypot, ceil
import json
from pathlib import Path
from visuals import direction_index

WIDTH, HEIGHT = 1280, 800
LEFT, RIGHT, BOTTOM, TOP = 76.0, 1204.0, 154.0, 666.0
GRAVITY = 880.0
PLAYER_HALF = 22.0
MAGAZINE_SIZE = 6
MAX_AMMO = 42
RELOAD_DURATION = 1.25
DEATH_DURATION = .8
ENEMY_BULLET_SPEED = 320.0


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

    @property
    def box(self):
        # y is the foot anchor plus 22px. Include the sprite's head and torso.
        return self.x-15, self.y-22, self.x+15, self.y+48


@dataclass
class Crate:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    held: bool = False

    @property
    def box(self):
        return self.x-23, self.y-23, self.x+23, self.y+23


@dataclass
class Bullet:
    x: float
    y: float
    vx: float
    vy: float
    owner: str
    life: float = 3.0


class Game:
    def __init__(self, level_path=None):
        level_path = level_path or Path(__file__).with_name("levels.json")
        self.levels = json.loads(Path(level_path).read_text(encoding="utf-8"))["rooms"]
        self.state = "title"
        self.age = 20
        self.room_index = 0
        self.mode = 2
        self.player = Actor(160.0, BOTTOM+PLAYER_HALF)
        self.enemies = []
        self.crates = []
        self.bullets = []
        self.obstacles = []
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

    @property
    def room(self):
        return self.levels[self.room_index]

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
        dx,dy = aim[0]-actor.x, aim[1]-actor.y-24
        if self.mode == 2:
            return (1.0 if dx >= 0 else -1.0), 0.0
        return unit(dx,dy)

    def advance_deaths(self, dt):
        for actor in [self.player]+self.enemies:
            if not actor.alive:
                actor.death_elapsed = min(DEATH_DURATION+3, actor.death_elapsed+dt)

    def message(self, text, seconds=2.4):
        self.hint, self.hint_left = text, seconds

    def start(self):
        self.age, self.room_index, self.mode = 20, 0, 2
        self.magazine, self.reserve = MAGAZINE_SIZE, MAX_AMMO-MAGAZINE_SIZE
        self.shots = self.kills = self.total_deaths = self.streak = 0
        self.elapsed = 0.0
        self.load_room()

    def load_room(self, retry=False):
        self.state = "playing"
        self.mode = 2
        self.player = Actor(*self.room.get("spawn", [160, 176]))
        self.enemies = [Actor(float(e[0]), float(e[1]), e[2], timer=2.2+i*.45, facing=4)
                        for i, e in enumerate(self.room["enemies"])]
        self.crates = [Crate(float(x), float(y)) for x, y in self.room["crates"]]
        self.obstacles = [tuple(o) for o in self.room.get("obstacles", [])]
        self.ammo_pickups = [list(p) for p in self.room.get("ammo", [])]
        self.settle_initial_layout()
        errors = self.layout_errors()
        if errors:
            raise ValueError(f"Invalid room {self.room_index+1}: " + "; ".join(errors))
        self.bullets, self.effects, self.events = [], [], []
        self.history.clear()
        self.world_time = 0.0
        self.time_left = 0.0
        self.time_frozen = False
        self.reload_left = self.shot_cooldown = 0.0
        self.clear = False
        self.grace = 1.2
        if retry:
            self.magazine, self.reserve = self.entry_ammo
        else:
            self.entry_ammo = self.magazine, self.reserve
        self.history.append((0.0, self.player.x, self.player.y))
        self.message(self.room["hint"], 6.0)

    def settle_initial_layout(self):
        """Place objects on support without simulating damaging startup falls."""
        supports = list(self.obstacles)
        for crate in sorted(self.crates, key=lambda c: c.y):
            tops = [r[3] for r in supports
                    if crate.x+23 > r[0] and crate.x-23 < r[2]
                    and r[3] <= crate.y-23+.5]
            crate.y = max([BOTTOM] + tops) + 23
            crate.vx = crate.vy = 0.0
            supports.append(crate.box)
        for actor in [self.player] + self.enemies:
            tops = [r[3] for r in supports
                    if actor.x+15 > r[0] and actor.x-15 < r[2]
                    and r[3] <= actor.y-PLAYER_HALF+.5]
            actor.y = max([BOTTOM] + tops) + PLAYER_HALF
            actor.vy = 0.0

    def layout_errors(self):
        """Reject room entries inside cover instead of hiding authoring errors."""
        errors = []
        actors = [self.player] + self.enemies
        for index, actor in enumerate(actors):
            label = "player" if index == 0 else f"enemy {index}"
            x1,y1,x2,y2 = actor.box
            if x1 < LEFT or x2 > RIGHT or y1 < BOTTOM-.5 or y2 > TOP:
                errors.append(f"{label} outside room")
            if any(self.overlap(actor.box, rect) for rect in self.solids()):
                errors.append(f"{label} overlaps cover")
            if any(self.overlap(actor.box, other.box) for other in actors[:index]):
                errors.append(f"{label} overlaps another actor")
        for index, crate in enumerate(self.crates):
            x1,y1,x2,y2 = crate.box
            if x1 < LEFT or x2 > RIGHT or y1 < BOTTOM-.5 or y2 > TOP:
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
        if mode == 2:
            for actor in [self.player]+self.enemies:
                if actor.alive:
                    actor.facing = 4 if actor.facing in (3,4,5) else 0
        self.player.vy = 0.0
        if old_mode == 2 and mode in (3, 4):
            # Height velocity does not become motion across the reinterpreted floor.
            for crate in self.crates:
                crate.vy = 0.0
            for enemy in self.enemies:
                enemy.vy = 0.0
        if mode == 4:
            self.time_left, self.selected = 10.0, 0
            self.message("정지 중에도 10초 제한은 흐릅니다. 휠로 과거 선택, Enter로 이동", 4.5)
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

    def safe_position(self, x, y):
        if not LEFT+16 <= x <= RIGHT-16 or not BOTTOM+PLAYER_HALF <= y <= TOP-48:
            return False
        box = (x-14, y-21, x+14, y+47)
        if any(self.overlap(box, r) for r in self.obstacles):
            return False
        if any(not c.held and self.overlap(box, c.box) for c in self.crates):
            return False
        return not any(e.alive and hypot(x-e.x, y-e.y) < 38 for e in self.enemies)

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
            self.held.x, self.held.y = x, y+49
        self.leave_time()
        self.events.append("rewind")
        self.message(f"{ago:g}초 전 위치로 이동 / 나이 +1")
        return True

    def pickup(self):
        if self.state != "playing":
            return False
        if self.clear and self.player.x > RIGHT-110:
            return self.next_room()
        if self.held:
            self.message("Q로 물체를 던질 수 있습니다")
            return False
        near = [c for c in self.crates if hypot(c.x-self.player.x, c.y-self.player.y) < 104]
        if not near:
            self.message("가까운 상자에 다가가 E를 누르세요")
            return False
        crate = min(near, key=lambda c: hypot(c.x-self.player.x, c.y-self.player.y))
        crate.held, crate.vx, crate.vy = True, 0.0, 0.0
        self.events.append("pickup")
        return True

    def throw(self, aim):
        crate = self.held
        if not crate or self.state != "playing":
            return False
        dx, dy = self.aim_direction(aim)
        crate.held = False
        crate.x = clamp(self.player.x+dx*48, LEFT+24, RIGHT-24)
        crate.y = clamp(self.player.y+dy*48, BOTTOM+24, TOP-24)
        crate.vx, crate.vy = dx*480, dy*480+(100 if self.mode == 2 else 0)
        self.events.append("throw")
        return True

    def reload(self):
        if self.state == "playing" and self.magazine < MAGAZINE_SIZE and self.reserve and self.reload_left <= 0:
            self.reload_left = RELOAD_DURATION
            self.events.append("reload")
            return True
        return False

    def shoot(self, aim):
        if self.state != "playing" or self.reload_left > 0 or self.shot_cooldown > 0:
            return False
        if self.magazine <= 0:
            self.message("탄창이 비었습니다. R로 장전하세요", 1.0)
            return False
        muzzle_y = self.player.y+24
        dx, dy = self.aim_direction(aim)
        self.player.facing = direction_index(dx,dy,self.mode)
        self.bullets.append(Bullet(self.player.x+dx*25, muzzle_y+dy*25, dx*850, dy*850, "player"))
        self.shot_cooldown, self.magazine = .22, self.magazine-1
        self.shots += 1
        self.events.append("shot")
        self.effects.append([self.player.x+dx*29, muzzle_y+dy*29, .1, "flash"])
        return True

    @staticmethod
    def overlap(a, b):
        return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]

    def solids(self, skip=None):
        return self.obstacles + [c.box for c in self.crates if not c.held and c is not skip]

    def move_actor(self, actor, dx, dy, dt, gravity=False):
        before_x,before_y = actor.x,actor.y
        actor.x += dx
        actor.x = clamp(actor.x, LEFT+16, RIGHT-16)
        for box in self.solids():
            if self.overlap(actor.box, box):
                if dx > 0: actor.x = box[0]-15
                elif dx < 0: actor.x = box[2]+15
        old_y = actor.y
        if gravity:
            actor.vy -= GRAVITY*dt
            dy = actor.vy*dt
        actor.y = clamp(actor.y+dy, BOTTOM+PLAYER_HALF, TOP-48)
        if actor.y == BOTTOM+PLAYER_HALF:
            actor.vy = 0
        for box in self.solids():
            if self.overlap(actor.box, box):
                if dy < 0 and old_y-PLAYER_HALF >= box[3]-.5:
                    actor.y, actor.vy = box[3]+PLAYER_HALF, 0
                elif dy > 0:
                    actor.y, actor.vy = box[1]-48, 0
                elif not gravity and abs(dx) < .001:
                    actor.y = old_y
        distance = hypot(actor.x-before_x, 0 if gravity else actor.y-before_y)
        actor.moving = distance > .001
        if actor.moving:
            actor.walk_distance += distance

    def update_crates(self, dt):
        for c in self.crates:
            if c.held:
                c.x, c.y = self.player.x, min(TOP-24, self.player.y+49)
                continue
            if self.mode == 2:
                c.vy -= GRAVITY*dt
            else:
                c.vx *= max(0, 1-1.5*dt)
                c.vy *= max(0, 1-1.5*dt)
            old_x, old_y = c.x, c.y
            c.x += c.vx*dt
            c.y += c.vy*dt
            impact = hypot(c.vx, c.vy)
            for enemy in self.enemies:
                if enemy.alive and impact > 125 and self.overlap(c.box, enemy.box):
                    self.kill(enemy)
            if c.y < BOTTOM+23:
                c.y, c.vy, c.vx = BOTTOM+23, 0.0, c.vx*.72
            if c.x < LEFT+23 or c.x > RIGHT-23:
                c.x, c.vx = clamp(c.x, LEFT+23, RIGHT-23), -c.vx*.3
            if c.y > TOP-23:
                c.y, c.vy = TOP-23, 0
            for box in self.solids(skip=c):
                if self.overlap(c.box, box):
                    if old_y-23 >= box[3]-.5 and c.vy <= 0:
                        c.y, c.vy, c.vx = box[3]+23, 0, c.vx*.8
                    elif old_y+23 <= box[1]+.5 and c.vy > 0:
                        c.y, c.vy = box[1]-23, 0
                    elif old_x < c.x:
                        c.x, c.vx = box[0]-23, 0
                    elif old_x > c.x:
                        c.x, c.vx = box[2]+23, 0

    def kill(self, enemy):
        if enemy.alive:
            enemy.alive = False
            enemy.moving = False
            enemy.death_elapsed = 0.0
            self.kills += 1
            self.effects.append([enemy.x, enemy.y, .45, "hit"])
            self.events.append("hit")

    def blocked(self, x1, y1, x2, y2):
        return any(segment_box(x1, y1, x2, y2, b) is not None for b in self.solids())

    def update_enemies(self, dt):
        for e in self.enemies:
            if not e.alive:
                continue
            dx, dy = unit(self.player.x-e.x, self.player.y-e.y)
            e.facing = direction_index(dx,dy,self.mode)
            if e.kind == "hunter":
                speed = 76+self.room_index*8
                self.move_actor(e, dx*speed*dt, dy*speed*dt if self.mode != 2 else 0, dt, self.mode == 2)
            else:
                self.move_actor(e, 0, 0, dt, self.mode == 2)
                if self.mode == 2:
                    e.aim_y = e.y+24
                if self.grace <= 0 and not self.clear:
                    e.timer -= dt
                    if e.timer <= .8 and not e.winding:
                        e.winding = True
                    if e.winding and e.timer > .15:
                        e.aim_x, e.aim_y = self.player.x, self.player.y+24
                        if self.mode == 2:
                            e.aim_y = e.y+24
                    if e.timer <= 0:
                        if not self.blocked(e.x, e.y+24, e.aim_x, e.aim_y):
                            ax, ay = self.aim_direction((e.aim_x,e.aim_y),e)
                            speed = ENEMY_BULLET_SPEED+self.room_index*25
                            self.bullets.append(Bullet(e.x+ax*25, e.y+24+ay*25, ax*speed, ay*speed, "enemy", 6.0))
                            self.events.append("enemy_shot")
                        e.winding = False
                        e.timer = 2.5-self.room_index*.12
            if self.grace <= 0 and self.overlap(self.player.box, e.box):
                self.die()
                return

    def update_bullets(self, dt):
        kept = []
        for b in self.bullets:
            nx, ny = b.x+b.vx*dt, b.y+b.vy*dt
            best_t, hit_actor = 2.0, None
            for rect in self.solids():
                t = segment_box(b.x, b.y, nx, ny, rect, 2)
                if t is not None and t < best_t:
                    best_t, hit_actor = t, None
            targets = [e for e in self.enemies if e.alive] if b.owner == "player" else [self.player]
            for actor in targets:
                t = segment_box(b.x, b.y, nx, ny, actor.box, 2)
                if t is not None and t < best_t:
                    best_t, hit_actor = t, actor
            if best_t <= 1:
                if hit_actor is self.player:
                    if self.grace <= 0:
                        self.die()
                elif hit_actor is not None:
                    self.kill(hit_actor)
                self.effects.append([b.x+(nx-b.x)*best_t, b.y+(ny-b.y)*best_t, .2, "spark"])
                continue
            b.x, b.y, b.life = nx, ny, b.life-dt
            if b.life > 0 and LEFT-10 < nx < RIGHT+10 and BOTTOM-10 < ny < TOP+10:
                kept.append(b)
        self.bullets = kept

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
        self.effects = [[x, y, life-dt, kind] for x, y, life, kind in self.effects if life > dt]
        if self.mode == 4:
            self.time_left -= dt
            if self.time_left <= 0:
                self.leave_time()
                if self.state != "playing":
                    return
        mx, my = move
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
        if self.held:
            self.held.x, self.held.y = self.player.x, min(TOP-24, self.player.y+49)
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
            self.message("방 클리어! Enter 또는 오른쪽 출구로 다음 방", 30)
            self.events.append("clear")
        if self.clear and self.player.x >= RIGHT-29:
            self.next_room()
