"""Render extreme aiming pitches at larger scale for waist/arm visual QA."""
import argparse
import math
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from main import App, INK, MUTED, CYAN
import pico2d as p

app=App(argparse.Namespace(smoke=True,smoke_scene='title',smoke_room=1,capture=None))
app.background()
app.text('CONNECTED WAIST / FLEXIBLE AIM',100,625,26,INK)
app.text('Fixed belt, small torso lean, independent shoulder and arm movement',100,591,16,MUTED)
for row,facing in enumerate((0,4)):
    y=475-row*200
    for col,degrees in enumerate((-85,-45,0,45,75,90)):
        x=150+col*190
        angle=math.radians(degrees)*(1 if facing==0 else -1)
        app.character_layers(('idle',facing),('idle',facing),x,y,150,angle=angle)
        app.text(f'{degrees:+d}',x-20,y-100,16,CYAN)
app.text('Torso mesh remains attached to the legs, including near-vertical aiming.',100,95,16,MUTED)
app.screenshot(str(root/'docs'/'connected-aim.png'))
p.update_canvas();app.motion_atlases.clear();del app.atlas,app.characters;p.close_canvas()
