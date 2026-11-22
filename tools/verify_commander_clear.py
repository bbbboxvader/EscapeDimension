"""Receding-horizon dodging bot using normal game damage, movement and ammunition."""
import json,math,sys
from copy import deepcopy
from pathlib import Path
repo=Path(__file__).resolve().parents[1];sys.path.insert(0,str(repo))
from core import Game

g=Game();g.room_index=11;g.load_room();g.grace=0
moves=[(0,0),(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)]
used=set();bombs_seen=0

def step(game,move,dt=.05):
    if game.magazine==0 and game.reload_left<=0:game.reload()
    b=game.command_window.box
    game.tick(dt,move,((b[0]+b[2])/2,(b[1]+b[3])/2),True)

def risk(game):
    if game.state!='playing':return 1e6
    l,b,r,t=game.movement_bounds();x,y=game.player.x,game.player.y
    value=math.hypot(x-(l+r)/2,y-(b+t)/2)*.0003
    for beam in game.lasers:
        delay=max(0,beam.warning-beam.age)
        if delay<.35 and game.overlap(game.player.box,beam.box):value+=4*(.4-delay)
    for bomb in game.grenades:
        remaining=max(0,min(bomb.flight_time-bomb.age,bomb.fuse))
        bx,by=bomb.x+bomb.vx*remaining,bomb.y+bomb.vy*remaining
        distance=game.distance_to_rect(bx,by,game.player.box)
        value+=max(0,bomb.radius*.7+30-distance)*.12/(bomb.fuse+.2)
    return value

for frame in range(400):
    # Search control sequences, including moving briefly and then stopping.
    # The full simulator predicts new waves, fuses and reloads with no immunity.
    beam=[(0.,g,None)]
    for depth in range(9):
        options=[]
        for cost,game,first in beam:
            for move in moves:
                sim=deepcopy(game)
                step(sim,move);step(sim,move)
                if sim.state!='playing':continue
                first_move=move if first is None else first
                options.append((cost+risk(sim)+.002*math.hypot(*move),sim,first_move))
        if not options:break
        options.sort(key=lambda n:n[0]);beam=[];cells=set()
        for option in options:
            sim=option[1];cell=(round(sim.player.x/10),round(sim.player.y/10))
            if cell in cells:continue
            cells.add(cell);beam.append(option)
            if len(beam)>=7:break
    if not beam:raise AssertionError('No safe input sequence found')
    move=min(beam,key=lambda n:n[0])[2] or (0,0)
    for _ in range(2):
        step(g,move);used.update(l.side for l in g.lasers);bombs_seen=max(bombs_seen,len(g.grenades))
        if g.command_window.hp<=0 or g.state!='playing':break
    if g.command_window.hp<=0 or g.state!='playing':break
if g.command_window.hp==0 and g.clear:g.next_room()
report={'state':g.state,'window_hp':g.command_window.hp,'seconds':round(g.elapsed,2),
        'shots':g.shots,'deaths':g.total_deaths,'sides_seen':sorted(used),'bombs_seen_at_once':bombs_seen,'age':g.age,
        'controls':'Normal movement, firing and reload; no invulnerability or damage overrides.'}
print(json.dumps(report))
assert g.command_window.hp==0 and g.total_deaths==0 and used=={'left','right','top','bottom'}
(repo/'verification'/'commander-clear.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
