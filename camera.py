"""Pure scrolling camera geometry; input and drawing share one transform."""
from dataclasses import dataclass
from core import LEFT,RIGHT,BOTTOM,TOP,clamp

@dataclass
class Camera:
    x: float = 0.0
    y: float = 0.0

    def follow(self, player, bounds):
        left,bottom,right,top=bounds
        self.x=clamp(player.x-(LEFT+RIGHT)/2,left-LEFT,max(left-LEFT,right-RIGHT))
        self.y=clamp(player.y-(BOTTOM+TOP)/2,bottom-BOTTOM,max(bottom-BOTTOM,top-TOP))

    def to_screen(self,x,y):return x-self.x,y-self.y

    def to_world(self,x,y):return x+self.x,y+self.y
