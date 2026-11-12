"""Pure direction and atlas geometry shared by the renderer and tests."""
from math import atan2, floor, pi

DIRECTIONS = ('E', 'NE', 'N', 'NW', 'W', 'SW', 'S', 'SE')


def direction_index(dx, dy):
    """Counter-clockwise octant; screen y points upward like the simulation."""
    if abs(dx)+abs(dy) < .001:
        return 0
    return floor((atan2(dy, dx)+pi/8)/(pi/4)) % 8


def atlas_region(frame, width, height):
    """4x4 grid; proportional edges also handle non-divisible image dimensions."""
    if not 0 <= frame < 16:
        raise ValueError('Character frame must be between 0 and 15')
    col, row = frame % 4, frame // 4
    x1, x2 = round(col*width/4), round((col+1)*width/4)
    y1, y2 = round(row*height/4), round((row+1)*height/4)
    return x1, height-y2, x2-x1, y2-y1
