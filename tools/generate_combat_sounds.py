"""Generate original grenade launch and explosion SFX; no external audio."""
from array import array
from pathlib import Path
import math,random,wave

root=Path(__file__).resolve().parents[1]
rate=22050
for name,duration in [('grenade',.22),('explosion',.65),('machinegun',.075),('glass_hit',.12),('glass_break',.6),('laser_charge',.28),('laser_fire',.35)]:
    rng=random.Random(46)
    samples=array('h')
    for i in range(round(rate*duration)):
        t=i/rate;noise=rng.uniform(-1,1)
        if name=='grenade':value=(math.sin(2*math.pi*(110*t+180*t*t))*.7+noise*.3)*math.exp(-t*18)
        elif name=='explosion':value=(noise*.72+math.sin(2*math.pi*(55*t-15*t*t))*.28)*math.exp(-t*7)
        elif name=='machinegun':value=(noise*.7+math.sin(2*math.pi*150*t)*.3)*math.exp(-t*45)*.65
        elif name=='glass_hit':value=(noise*.45+math.sin(2*math.pi*2400*t)*.25+math.sin(2*math.pi*3900*t)*.3)*math.exp(-t*32)*.6
        elif name=='glass_break':value=noise*(.6+.4*math.sin(2*math.pi*36*t))*math.exp(-t*7)*.75
        elif name=='laser_charge':value=math.sin(2*math.pi*(420*t+1100*t*t))*math.sin(math.pi*t/duration)*.38
        else:value=(math.sin(2*math.pi*(190*t-120*t*t))*.75+noise*.25)*math.exp(-t*11)*.65
        samples.append(round(value*18000))
    with wave.open(str(root/'assets'/(name+'.wav')),'wb') as out:
        out.setparams((1,2,rate,len(samples),'NONE','not compressed'))
        out.writeframes(samples.tobytes())
