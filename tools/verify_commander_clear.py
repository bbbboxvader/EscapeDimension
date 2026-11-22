"""A deterministic dodging bot, using normal movement/shoot/reload and damage."""
import json,math,sys
from pathlib import Path
repo=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(repo))
from core import Game,clamp
g=Game();g.room_index=11;g.load_room();g.grace=0
moves=[(0,0),(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)]
used=set()
for frame in range(2400):
    left,bottom,right,top=g.movement_bounds(g.player)
    def score(move):
        dx,dy=move;length=max(1,math.hypot(dx,dy));dx/=length;dy/=length
        value=math.hypot(*move)*.4
        for ahead in (.025,.1,.3,.6,.9,1.3):
            x=clamp(g.player.x+dx*g.speed*ahead,left+16,right-16)
            y=clamp(g.player.y+dy*g.speed*ahead,bottom+22,top-48)
            for laser in g.lasers:
                box=((min(g.player.x,x)-16,min(g.player.y,y)-22,max(g.player.x,x)+16,max(g.player.y,y)+48)
                     if laser.active else (x-16,y-22,x+16,y+48))
                if laser.warning<=laser.age+ahead<laser.warning+laser.duration and g.overlap(box,laser.box):
                    value+=100/(ahead+.1)
        x=clamp(g.player.x+dx*g.speed*.3,left+16,right-16)
        y=clamp(g.player.y+dy*g.speed*.3,bottom+22,top-48)
        value+=math.hypot(x-(left+right)/2,y-(bottom+top)/2)*.002
        return value
    move=min(moves,key=score)
    if g.magazine==0 and g.reload_left<=0:g.reload()
    box=g.command_window.box
    g.tick(.025,move,((box[0]+box[2])/2,(box[1]+box[3])/2),True)
    used.update(l.side for l in g.lasers)
    if g.command_window.hp<=0 or g.state!='playing':break
if g.command_window.hp==0 and g.clear:g.next_room()
report={'state':g.state,'window_hp':g.command_window.hp,'seconds':round((frame+1)*.025,2),
        'shots':g.shots,'deaths':g.total_deaths,'sides_seen':sorted(used),'age':g.age}
print(json.dumps(report))
(repo/'verification'/'commander-clear.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert g.command_window.hp==0 and g.total_deaths==0 and used=={'left','right','top','bottom'}
