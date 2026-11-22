"""Scrolling and quarter-turn camera; one reversible transform for aim/drawing."""
from dataclasses import dataclass
from core import LEFT,RIGHT,BOTTOM,TOP,clamp
from space import turn_point,turn_box

@dataclass
class Camera:
    x: float = 0.0
    y: float = 0.0
    turns: int = 0
    scale: float = 1.0

    def follow(self,player,bounds,arena=None,turns=0):
        self.turns=turns%4;self.scale=1.
        cx,cy=(LEFT+RIGHT)/2,(BOTTOM+TOP)/2
        if arena is not None:
            l,b,r,t=turn_box(arena,turns)
            self.scale=min(1.,(RIGHT-LEFT)/(r-l),(TOP-BOTTOM)/(t-b))
            self.x,self.y=(l+r)/2-cx,(b+t)/2-cy
            return
        l,b,r,t=turn_box(bounds,turns);px,py=turn_point(player.x,player.y,turns)
        w,h=(RIGHT-LEFT)/2,(TOP-BOTTOM)/2
        self.x=(clamp(px,l+w,r-w) if r-l>=w*2 else (l+r)/2)-cx
        self.y=(clamp(py,b+h,t-h) if t-b>=h*2 else (b+t)/2)-cy

    def to_screen(self,x,y):
        x,y=turn_point(x,y,self.turns);cx,cy=(LEFT+RIGHT)/2,(BOTTOM+TOP)/2
        return cx+(x-self.x-cx)*self.scale,cy+(y-self.y-cy)*self.scale

    def to_world(self,x,y):
        cx,cy=(LEFT+RIGHT)/2,(BOTTOM+TOP)/2
        return turn_point((x-cx)/self.scale+cx+self.x,(y-cy)/self.scale+cy+self.y,-self.turns)

    def vector(self,x,y):
        x,y=turn_point(x,y,self.turns);return x*self.scale,y*self.scale

    def box(self,rect):
        l,b,r,t=rect
        points=[self.to_screen(x,y) for x,y in ((l,b),(l,t),(r,b),(r,t))]
        return min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)
