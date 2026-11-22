"""Observation-window objective and telegraphed four-direction laser geometry."""
from dataclasses import dataclass

@dataclass
class ObservationWindow:
    box: tuple
    hp: int = 36
    max_hp: int = 36
    hit_flash: float = 0.0

    @property
    def damage_stage(self):
        if self.hp<=0:return 3
        return min(2,(self.max_hp-self.hp)*3//self.max_hp)

@dataclass
class LaserBeam:
    x1: float
    y1: float
    x2: float
    y2: float
    side: str
    warning: float = 1.05
    duration: float = .55
    age: float = 0.0
    width: float = 18.0

    @property
    def active(self):return self.warning<=self.age<self.warning+self.duration

    @property
    def finished(self):return self.age>=self.warning+self.duration

    @property
    def box(self):
        half=self.width/2
        return min(self.x1,self.x2)-half,min(self.y1,self.y2)-half,max(self.x1,self.x2)+half,max(self.y1,self.y2)+half
