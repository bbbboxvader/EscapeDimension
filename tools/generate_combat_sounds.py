"""Generate original grenade launch and explosion SFX; no external audio."""
from array import array
from pathlib import Path
import math,random,wave

root=Path(__file__).resolve().parents[1]
rate=22050
for name,duration in [('grenade',.22),('explosion',.65)]:
    rng=random.Random(46)
    samples=array('h')
    for i in range(round(rate*duration)):
        t=i/rate;noise=rng.uniform(-1,1)
        if name=='grenade':value=(math.sin(2*math.pi*(110*t+180*t*t))*.7+noise*.3)*math.exp(-t*18)
        else:value=(noise*.72+math.sin(2*math.pi*(55*t-15*t*t))*.28)*math.exp(-t*7)
        samples.append(round(value*18000))
    with wave.open(str(root/'assets'/(name+'.wav')),'wb') as out:
        out.setparams((1,2,rate,len(samples),'NONE','not compressed'))
        out.writeframes(samples.tobytes())
