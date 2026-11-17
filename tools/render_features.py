"""Capture the game's actual layered renderer for visual verification."""
import argparse
from pathlib import Path
import sys
import math
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from main import App, INK, MUTED, CYAN, RED
from core import Actor, RELOAD_DURATION
import pico2d as p

args=argparse.Namespace(smoke=True,smoke_scene='title',smoke_room=1,capture=None)
app=App(args);app.game.start();app.background()
app.text('PURSUIT / AIM / MOVING RELOAD',100,625,26,INK)
app.text('Actual pico2d renderer / torso and legs use independent sprite regions',100,591,14,MUTED)
app.text('2D AIM',100,495,16,CYAN)
app.game.mode=2
for index,(side,dy) in enumerate(((1,200),(1,-150),(-1,200),(-1,-150))):
    actor=Actor(365+index*210,480)
    target=actor.x+side*250,actor.y+24+dy
    app.actor(actor,target,player=True)
app.text('RELOAD + WALK',100,349,16,CYAN)
app.game.mode=3
for index,facing in enumerate((0,0,4,4)):
    angle=facing*math.pi/4
    actor=Actor(365+index*210,334,moving=True,walk_distance=0 if index%2==0 else 33)
    app.game.reload_left=RELOAD_DURATION*(.8 if index<2 else .3)
    app.actor(actor,(actor.x+math.cos(angle)*200,actor.y+24+math.sin(angle)*200),player=True)
app.text('KNIFE RUNNER',100,204,16,RED)
for index,facing in enumerate((0,0,4,4)):
    actor=Actor(365+index*210,189,'knife',moving=True,
                walk_distance=0 if index%2==0 else 33,facing=facing)
    app.actor(actor,(actor.x+100,actor.y))
app.text('Fast blade enemy / cover-aware navigation / upward and downward 2D fire',100,95,16,MUTED)
app.screenshot(str(root/'docs'/'pursuit-layering.png'))
p.update_canvas();app.motion_atlases.clear();del app.atlas,app.characters;p.close_canvas()
