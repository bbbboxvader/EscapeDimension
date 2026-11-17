"""Pure direction and atlas geometry shared by the renderer and tests."""
from math import atan2, floor, pi, sin, cos

DIRECTIONS = ('E', 'NE', 'N', 'NW', 'W', 'SW', 'S', 'SE')


def torso_angle(dx, dy):
    """Side-view torso pitch around the belt; legs keep their left/right pose."""
    angle=atan2(dy,max(abs(dx),.001))
    return -angle if dx<0 else angle


def smoothstep(low, high, value):
    t=max(0,min(1,(value-low)/(high-low)))
    return t*t*(3-2*t)


def deform_upper_point(x, y, angle, side):
    """Skin a normalized sprite point: fixed belt, small chest lean, aiming arm.

    Coordinates are relative to the centre of a square sprite. Vertices at or
    below the belt stay fixed, so the upper body cannot separate from the legs.
    """
    waist=-.05
    if y<=waist:
        return x,y
    lean=max(-.18,min(.18,angle*.15))
    body_weight=smoothstep(waist,.18,y)
    bend=lean*body_weight
    px=x*cos(bend)-(y-waist)*sin(bend)
    py=waist+x*sin(bend)+(y-waist)*cos(bend)
    arm_weight=(smoothstep(.02,.24,side*x)*smoothstep(.04,.12,y)
                *(1-smoothstep(.31,.39,y)))
    shoulder_x=-(.18-waist)*sin(lean)
    shoulder_y=waist+(.18-waist)*cos(lean)
    turn=angle-lean
    ax=shoulder_x+(px-shoulder_x)*cos(turn)-(py-shoulder_y)*sin(turn)
    ay=shoulder_y+(px-shoulder_x)*sin(turn)+(py-shoulder_y)*cos(turn)
    return px+(ax-px)*arm_weight,py+(ay-py)*arm_weight


def direction_index(dx, dy, mode=3):
    """Counter-clockwise octant; screen y points upward like the simulation."""
    if mode == 2:
        return 0 if dx >= 0 else 4
    if abs(dx)+abs(dy) < .001:
        return 0
    return floor((atan2(dy, dx)+pi/8)/(pi/4)) % 8


def motion_frame(facing, distance, moving=False, reload_progress=None,
                 death_elapsed=None, enemy=False, death_duration=.8):
    """Select real sprite frames; caller owns clocks so pausing freezes poses."""
    if death_elapsed is not None:
        left = facing in (3,4,5)
        row = (2 if enemy else 0) + int(left)
        return 'death_both', row*4 + min(3, int(death_elapsed/death_duration*4))
    if reload_progress is not None and not enemy:
        # Reach for magazine -> insert magazine -> return to the ready pose.
        phase = 0 if reload_progress < .45 else 1
        return 'reload_player', phase*8+facing
    if moving:
        phase = int(distance/32) % 2
        return 'walk_enemy' if enemy else 'walk_player', phase*8+facing
    return 'idle', facing+(8 if enemy else 0)


def atlas_region(frame, width, height):
    """4x4 grid; proportional edges also handle non-divisible image dimensions."""
    if not 0 <= frame < 16:
        raise ValueError('Character frame must be between 0 and 15')
    col, row = frame % 4, frame // 4
    x1, x2 = round(col*width/4), round((col+1)*width/4)
    y1, y2 = round(row*height/4), round((row+1)*height/4)
    return x1, height-y2, x2-x1, y2-y1
