"""Python + pico2d desktop game. Run main.py or the packaged Windows EXE."""
from __future__ import annotations
import argparse
import ctypes
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time

# Keep main.py as the entry point even when launched with the system Python.
# The project environment owns its pico2d / SDL dependencies.
if __name__ == '__main__' and not getattr(sys, 'frozen', False):
    project_root = Path(__file__).resolve().parent
    project_env = project_root / '.venv'
    project_python = project_env / 'Scripts' / 'python.exe'
    if project_python.is_file() and Path(sys.prefix).resolve() != project_env.resolve():
        raise SystemExit(subprocess.call([str(project_python), str(Path(__file__).resolve()), *sys.argv[1:]]))

import pico2d as p
import pico2d.pico2d as api
from sdl2 import (SDL_SetWindowTitle, SDL_SetRenderDrawColor, SDL_RenderClear,
                  SDL_SetRenderDrawBlendMode, SDL_BLENDMODE_BLEND,
                  SDL_SetTextureAlphaMod, SDL_RenderReadPixels, SDL_PIXELFORMAT_ARGB8888,
                  SDL_GetMouseState, SDL_WINDOWEVENT, SDL_GetWindowFlags,
                  SDL_WINDOW_INPUT_FOCUS)

from core import (Game, WIDTH, HEIGHT, LEFT, RIGHT, BOTTOM, TOP, clamp,
                  MAGAZINE_SIZE, MAX_AMMO, RELOAD_DURATION, DEATH_DURATION)
from visuals import direction_index, atlas_region, motion_frame, torso_angle

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
ASSETS = ROOT / "assets"
INK = (39, 48, 62)
MUTED = (114, 124, 134)
CYAN = (5, 150, 177)
RED = (216, 81, 72)
PURPLE = (121, 90, 185)
PAPER = (250, 248, 241)


class App:
    def __init__(self, args):
        self.args = args
        self.game = Game(ROOT/"levels.json")
        self.keys = set()
        self.mouse = (820, 320)
        self.mouse_down = False
        self.paused = False
        self.help = False
        self.running = True
        self.muted = False
        self.ui_time = 0.0
        p.open_canvas(WIDTH, HEIGHT, sync=True)
        api.print_fps = lambda: None
        SDL_SetWindowTitle(api.window, b"Escape Dimension - Python + pico2d")
        p.hide_lattice()
        SDL_SetRenderDrawBlendMode(api.renderer, SDL_BLENDMODE_BLEND)
        p.hide_cursor()
        self.atlas = p.load_image(str(ASSETS/"sprites.png"))
        self.cw, self.ch = self.atlas.w//3, self.atlas.h//2
        self.characters = p.load_image(str(ASSETS/"characters_8dir.png"))
        self.motion_atlases = {'idle':self.characters}
        for name in ('walk_player','walk_enemy','reload_player','death_both','knife_enemy'):
            self.motion_atlases[name] = p.load_image(str(ASSETS/(name+'.png')))
        fonts = [Path("C:/Windows/Fonts/malgun.ttf"), Path(os.getenv("PICO2D_DATA_PATH", ""))/"ConsolaMalgun.TTF",
                 Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
        self.fontpath = next((f for f in fonts if f.is_file()), None)
        if not self.fontpath:
            raise RuntimeError("사용 가능한 글꼴을 찾을 수 없습니다.")
        self.fonts = {size:p.load_font(str(self.fontpath),size) for size in (14,16,18,20,23,26,32,42,66)}
        self.sounds = {}
        if api.audio_on:
            for name in ("shot","switch","hit","death","reload","pickup","clear","rewind","enemy_shot","win","throw"):
                f = ASSETS/(name+".wav")
                if f.exists():
                    self.sounds[name] = p.load_wav(str(f))
                    self.sounds[name].set_volume(28 if name == "shot" else 36)
        rng = random.Random(3)
        self.grain = [(rng.randrange(65,1210),rng.randrange(143,679),rng.choice((230,235,240))) for _ in range(300)]
        if args.smoke and args.smoke_scene not in ('title','directions','motions'):
            self.game.start()
            self.game.room_index = args.smoke_room-1
            self.game.load_room()
            if args.smoke_scene in ('3d','4d'):
                self.game.set_mode(3)
                for _ in range(100):
                    self.game.tick(.016, (1,.45), (870,250))
            else:
                for _ in range(40):self.game.tick(.016)
            if args.smoke_scene == '4d':
                self.game.set_mode(4)
                self.game.tick(.001)

    def text(self, value, x, y, size=18, color=INK):
        self.fonts[size].draw(x, y, str(value), color)

    @staticmethod
    def rect(x1,y1,x2,y2,color,filled=False,alpha=255):
        p.draw_rectangle(x1,y1,x2,y2,*color,alpha,filled)

    @staticmethod
    def line(x1,y1,x2,y2,color=INK,alpha=255):
        p.draw_line(x1,y1,x2,y2,*color,alpha)

    def sprite(self, cell, x,y,size=96,flip=False,alpha=255):
        col,row=cell%3,cell//3
        SDL_SetTextureAlphaMod(self.atlas.texture, int(clamp(alpha,0,255)))
        self.atlas.clip_composite_draw(col*self.cw, (1-row)*self.ch, self.cw,self.ch,0,"h" if flip else "",x,y,size,size)
        SDL_SetTextureAlphaMod(self.atlas.texture,255)

    def character_frame(self, frame, x, y, size=84, alpha=255, atlas='idle', angle=0):
        image = self.motion_atlases[atlas]
        region = atlas_region(frame, image.w, image.h)
        SDL_SetTextureAlphaMod(image.texture, int(clamp(alpha,0,255)))
        image.clip_composite_draw(*region,angle,'',x,y,size,size)
        SDL_SetTextureAlphaMod(image.texture,255)

    def character_layers(self, upper, lower, x, y, size=84, alpha=255, angle=0):
        """Compose legs and torso from source cells with a pivot at the belt."""
        bottom=y-size/2
        for part,(name,frame) in (('legs',lower),('torso',upper)):
            image=self.motion_atlases[name]
            sx,sy,sw,sh=atlas_region(frame,image.w,image.h)
            cut=round(sh*.45)
            SDL_SetTextureAlphaMod(image.texture,alpha)
            if part=='legs':
                height=size*cut/sh
                image.clip_draw(sx,sy,sw,cut,x,bottom+height/2,size,height+2)
            else:
                overlap=min(4,cut)
                height=size*(sh-cut+overlap)/sh
                waist=bottom+size*.45
                offset=height/2-size*overlap/sh
                image.clip_composite_draw(sx,sy+cut-overlap,sw,sh-cut+overlap,angle,'',
                                          x-math.sin(angle)*offset,
                                          waist+math.cos(angle)*offset,size,height)
            SDL_SetTextureAlphaMod(image.texture,255)

    def actor(self, actor, target, player=False, alpha=255):
        dx,dy = target[0]-actor.x, target[1]-(actor.y+24)
        facing = direction_index(dx,dy,self.game.mode) if player and actor.alive else actor.facing
        if player:
            self.player_facing = facing
        reload_progress = 1-self.game.reload_left/RELOAD_DURATION if player and self.game.reload_left>0 else None
        atlas,frame = motion_frame(facing,actor.walk_distance,actor.moving,
                                  reload_progress,actor.death_elapsed if not actor.alive else None,
                                  enemy=not player,death_duration=DEATH_DURATION)
        if player:
            self.player_motion = atlas,frame
            self.player_layers = None
        if not actor.alive and not player:
            alpha = int(max(95,255-max(0,actor.death_elapsed-1)*65))
        bob = abs(math.sin(actor.walk_distance*.15))*1.0 if actor.alive and actor.moving and reload_progress is None else 0
        shade = CYAN if player else RED
        self.line(actor.x-13,actor.y-21,actor.x+13,actor.y-21,shade,70)
        self.line(actor.x-8,actor.y-23,actor.x+8,actor.y-23,shade,35)
        knife=actor.kind=='knife'
        if knife:
            knife_frame=facing+(int(actor.walk_distance/32)%2)*8
            progress=clamp(actor.death_elapsed/DEATH_DURATION,0,1) if not actor.alive else 0
            angle=progress*math.pi/2*(-1 if facing in (3,4,5) else 1)
            self.character_frame(knife_frame,actor.x,actor.y+18-10*progress,84,alpha,'knife_enemy',angle)
            self.last_enemy_art='knife_enemy',knife_frame
        elif actor.alive and (self.game.mode==2 or reload_progress is not None):
            lower=motion_frame(facing,actor.walk_distance,actor.moving,enemy=not player)
            angle=torso_angle(dx,dy) if self.game.mode==2 and reload_progress is None else 0
            self.character_layers((atlas,frame),lower,actor.x,actor.y+18+bob,84,alpha,angle)
            if player:
                self.player_layers={'upper':(atlas,frame),'lower':lower,'angle':angle}
        else:
            self.character_frame(frame,actor.x,actor.y+18+bob,84,alpha,atlas)
            if player:self.player_layers=None
        if not player and actor.alive and actor.kind=='knife':
            self.text('KNIFE',actor.x-20,actor.y+70,14,(200,105,37))
        elif not player and actor.alive and actor.kind == 'hunter':
            self.text('!',actor.x-3,actor.y+70,14,(177,98,38))

    def events(self):
        for event in p.get_events():
            if event.type == p.SDL_QUIT:
                self.running=False
            elif event.type == p.SDL_KEYUP:
                self.keys.discard(event.key)
            elif event.type == p.SDL_KEYDOWN:
                was_down=event.key in self.keys
                self.keys.add(event.key)
                key=event.key
                if key==p.SDLK_ESCAPE:
                    if self.help:
                        self.help=False
                    elif self.game.state=="playing":
                        self.paused=not self.paused
                    else:
                        self.running=False
                elif key==p.SDLK_m:
                    self.muted=not self.muted
                elif key==p.SDLK_F1:
                    self.help=not self.help
                elif key==p.SDLK_RETURN:
                    if self.game.state=="title": self.game.start()
                    elif self.game.state in ("dead","over","won"):
                        if self.game.death_finished:self.game.retry()
                    elif not self.paused and not self.help:
                        if self.game.mode==4: self.game.rewind()
                        elif self.game.clear: self.game.next_room()
                elif self.game.state=="playing" and not self.paused and not self.help:
                    if key in (p.SDLK_2,p.SDLK_3,p.SDLK_4): self.game.set_mode(key-p.SDLK_0)
                    elif key==p.SDLK_r: self.game.reload()
                    elif key==p.SDLK_SPACE and not was_down: self.game.jump()
                    elif key==p.SDLK_e: self.game.pickup()
                    elif key==p.SDLK_q: self.game.throw(self.mouse)
                    elif key==p.SDLK_LEFT: self.game.select_rewind(-1)
                    elif key==p.SDLK_RIGHT: self.game.select_rewind(1)
            elif event.type == p.SDL_MOUSEMOTION:
                self.mouse=(event.x,HEIGHT-event.y)
            elif event.type == p.SDL_MOUSEBUTTONUP:
                if event.button==1:self.mouse_down=False
            elif event.type == p.SDL_MOUSEWHEEL:
                if self.game.mode==4:self.game.select_rewind(-event.y)
            elif event.type == p.SDL_MOUSEBUTTONDOWN and event.button==1:
                self.mouse=(event.x,HEIGHT-event.y)
                if self.game.state=="title":
                    if 505<self.mouse[0]<775 and 185<self.mouse[1]<243:self.game.start()
                elif self.game.mode==4 and self.mouse[1]<135:
                    points=self.game.rewind_points()
                    if points:
                        index=round((self.mouse[0]-334)/790*(len(points)-1))
                        self.game.select_rewind(index=index)
                else:
                    points=self.game.rewind_points() if self.game.mode==4 else []
                    near=[(math.hypot(x-self.mouse[0],y-self.mouse[1]),i) for i,(_,x,y,_) in enumerate(points)]
                    if near and min(near)[0]<25:self.game.select_rewind(index=min(near)[1])
                    else:self.mouse_down=True
        # Focus loss should never leave movement or firing latched.
        if not SDL_GetWindowFlags(api.window)&SDL_WINDOW_INPUT_FOCUS and not self.args.smoke:
            self.keys.clear();self.mouse_down=False

    def arrow(self,x,y,dx,dy,color=CYAN,length=29,alpha=255):
        endx,endy=x+dx*length,y+dy*length
        self.line(x,y,endx,endy,color,alpha)
        self.line(endx,endy,endx-dx*9-dy*5,endy-dy*9+dx*5,color,alpha)
        self.line(endx,endy,endx-dx*9+dy*5,endy-dy*9-dx*5,color,alpha)

    def background(self):
        SDL_SetRenderDrawColor(api.renderer,*PAPER,255);SDL_RenderClear(api.renderer)
        # A memo outline, not a perspective floor or wall.
        self.rect(64,142,1216,678,(222,218,207),True)
        self.rect(61,146,1213,682,(255,254,249),True)
        for x,y,v in self.grain:self.line(x,y,x+1,y,(v,v-1,v-4),120)
        self.rect(LEFT,BOTTOM,RIGHT,TOP,(178,177,167))
        for y in range(190,650,40):
            for x in range(105,1195,40):
                self.line(x,y,x+1,y,(209,211,204),100)
        for y in (240,400,560):
            p.draw_circle(69,y,3,207,205,194,200,True)
        self.line(94,157,94,659,(213,173,160),110)
        self.line(1177,678,1213,646,(218,214,200))
        self.line(1177,678,1177,646,(218,214,200))
        self.line(1177,646,1213,646,(218,214,200))
        self.text("ESCAPE DIMENSION",76,746,32)
        self.text("2D GAME PROGRAMMING / PYTHON + PICO2D",78,714,14,MUTED)

    def map_details(self):
        g=self.game
        accent={'cyan':CYAN,'gold':(159,126,55),'purple':PURPLE}.get(g.room.get('accent'),CYAN)
        for x1,y1,x2,y2,label in g.room.get('zones',[]):
            self.rect(x1,y1,x2,y2,accent,True,9)
            for x,y,sx,sy in ((x1,y1,1,1),(x2,y1,-1,1),(x1,y2,1,-1),(x2,y2,-1,-1)):
                self.line(x,y,x+sx*15,y,accent,80)
                self.line(x,y,x,y+sy*15,accent,80)
            self.text(label,x1+12,y2-20,14,(157,165,161))
        for x,y,label in g.room.get('marks',[]):
            self.text(label,x,y,14,(162,166,157))
        self.text(g.room.get('tag','FIELD NOTE'),92,573,14,accent)
        self.line(92,554,300,554,accent,80)
        self.text('IN',LEFT+19,BOTTOM+101,14,CYAN)
        self.arrow(LEFT+25,BOTTOM+74,1,0,CYAN,22,110)
        self.rect(RIGHT-25,BOTTOM+1,RIGHT-1,BOTTOM+90,(214,215,204),True,110)
        self.rect(RIGHT-25,BOTTOM+1,RIGHT-1,BOTTOM+90,(156,162,151))
        self.line(RIGHT-22,BOTTOM+85,RIGHT-4,BOTTOM+85,accent,150)
        self.text('EXIT',RIGHT-39,BOTTOM+107,14,accent)
        if g.mode==2:
            self.arrow(LEFT+35,455,0,-1,accent,30,130)
            self.text('G',LEFT+30,476,14,accent)

    def hud(self):
        g=self.game
        mode_colors={2:CYAN,3:(167,126,24),4:PURPLE}
        self.text(f"{g.mode}D",555,747,42,mode_colors[g.mode])
        label={2:"좌우 이동 + 중력",3:"8방향 자유 이동",4:"정지 + 과거 위치"}[g.mode]
        self.text(label,636,751,20,mode_colors[g.mode])
        self.text(f"AGE {g.age:02d} / 40",970,754,26,RED if g.age>=35 else INK)
        self.text(f"ROOM {g.room_index+1:02d} / {len(g.levels):02d}",970,715,18,MUTED)
        self.text(f"{g.magazine:02d}",79,97,42,CYAN if g.magazine else RED)
        self.text(f"/ {g.reserve:02d}",143,98,23,MUTED)
        self.text(f"합계 {g.total_ammo:02d} / {MAX_AMMO}",80,44,14,MUTED)
        self.text("R 장전" if not g.reload_left else f"장전 중 {g.reload_left:.1f}s",80,66,16,MUTED)
        self.text(f"{g.room['name']}   ·   남은 적 {sum(e.alive for e in g.enemies)}",92,638,20,MUTED)
        if g.mode==4:
            self.text(f"{g.time_left:04.1f}s",983,638,23,PURPLE)
            self.text("WORLD PAUSED" if g.time_frozen else "WORLD MOVING",880,610,14,PURPLE)
            self.rect(880,596,1158,600,(224,216,237),True)
            self.rect(880,596,880+278*max(0,g.time_left)/10,600,PURPLE,True)
        self.text("2 평면   3 자유 이동   4 시간   E 집기   Q 던지기   F1 도움말   ESC 일시정지",286,35,16,MUTED)
        if g.mode==2:
            self.text("A / D 좌우 이동   ·   SPACE 점프",293,101,20,CYAN)
            self.text("같은 종이가 지금은 높이로 읽힙니다",293,72,16,MUTED)
        elif g.mode==3:
            self.text("W / A / S / D 자유 이동",293,101,20,(152,115,27))
            self.text("원근 없는 같은 종이가 바닥이 됩니다",293,72,16,MUTED)
        else:self.timeline()
        if g.hint_left>0:
            self.text(g.hint,95,609,16,PURPLE if g.mode==4 else CYAN)
        if g.reload_left>0 and g.player.alive:
            progress=1-g.reload_left/RELOAD_DURATION
            self.rect(g.player.x-25,g.player.y-39,g.player.x+25,g.player.y-35,(219,221,216),True)
            self.rect(g.player.x-25,g.player.y-39,g.player.x-25+50*progress,g.player.y-35,CYAN,True)

    def timeline(self):
        g=self.game;points=g.rewind_points()
        self.text("과거 위치",250,110,18,PURPLE)
        self.line(334,95,1124,95,(197,184,216))
        if not points:
            self.text("움직임 기록이 필요합니다. 이동 후 4D를 사용하세요",346,108,16,MUTED)
            return
        g.selected=int(clamp(g.selected,0,len(points)-1))
        for i,(ago,x,y,safe) in enumerate(points):
            tx=334+(i/(len(points)-1) if len(points)>1 else 0)*790
            color=PURPLE if safe else RED
            p.draw_circle(tx,95,7 if i==g.selected else 4,*color,255,i==g.selected)
        ago,x,y,safe=points[g.selected]
        self.text(f"{ago:g}초 전 / {g.precision:g}초 간격  ·  휠·방향키 선택 / Enter 이동",334,65,16,PURPLE if safe else RED)

    def world(self):
        g=self.game
        self.map_details()
        if g.mode==4:
            points=g.rewind_points()
            for i,(_,x,y,safe) in enumerate(points):
                p.draw_circle(x,y,15 if i==g.selected else 9,*(PURPLE if safe else RED),100,False)
                if i==g.selected:self.character_frame(direction_index(self.mouse[0]-x,self.mouse[1]-y-24,g.mode),x,y+18,84,78)
        for rect in g.obstacles:
            x1,y1,x2,y2=rect
            self.rect(x1+3,y1-4,x2+3,y2-4,(160,164,155),True,38)
            self.rect(*rect,(231,229,216),True)
            for x in range(int(x1)+5,int(x2)-8,13):
                self.line(x,y1+3,x+7,y2-3,(191,192,177),130)
            self.rect(*rect,(136,145,135))
            self.line(x1+2,y2-2,x2-2,y2-2,(255,254,242))
            for x in (x1+6,x2-6):
                p.draw_circle(x,(y1+y2)/2,2,136,145,135,200,True)
        for pickup in g.ammo_pickups:
            self.sprite(5,*pickup,64)
        for crate in g.crates:
            if g.mode!=2:self.line(crate.x-18,crate.y-24,crate.x+18,crate.y-24,(181,177,154),90)
            self.sprite(4,crate.x,crate.y+3,79)
            if crate.held:self.text("Q",crate.x-6,crate.y+43,16,CYAN)
            elif math.hypot(crate.x-g.player.x,crate.y-g.player.y)<104:
                self.text("E 집기",crate.x-24,crate.y+43,14,CYAN)
        for e in g.enemies:
            if e.alive and e.winding and not g.clear:
                self.line(e.x,e.y+24,e.aim_x,e.aim_y,RED,145 if g.time_frozen else 220)
                p.draw_circle(e.aim_x,e.aim_y,10,*RED,145,False)
            target=(e.aim_x,e.aim_y) if e.winding else (g.player.x,g.player.y+24)
            self.actor(e,target)
        self.actor(g.player,self.mouse,player=True)
        if g.player.alive:
            dx,dy=g.aim_direction(self.mouse)
            muzzle_x,muzzle_y=g.muzzle_position(self.mouse)
            self.line(muzzle_x+dx*12,muzzle_y+dy*12,
                      muzzle_x+dx*20,muzzle_y+dy*20,CYAN,170)
        if g.grace>0 and g.player.alive:
            p.draw_circle(g.player.x,g.player.y,35,*CYAN,100,False)
        for b in g.bullets:
            color=CYAN if b.owner=="player" else RED
            p.draw_circle(b.x,b.y,4,*color,255,True)
            norm=math.hypot(b.vx,b.vy) or 1
            self.line(b.x-b.vx/norm*12,b.y-b.vy/norm*12,b.x,b.y,color)
        for x,y,life,kind in g.effects:
            color=RED if kind=="hit" else (211,166,38)
            if kind=='slash':color=(220,114,33)
            if kind=="flash":color=(218,161,25)
            radius=9 if kind=="flash" else int(25*(1-life/.45))
            p.draw_circle(x,y,max(2,radius),*color,int(clamp(life*700,0,255)),False)
        # Exit is only emphasized after combat, keeping the page nearly blank.
        if g.clear:
            self.rect(RIGHT-31,BOTTOM+7,RIGHT-7,BOTTOM+82,CYAN)
            self.text("NEXT",RIGHT-57,BOTTOM+97,16,CYAN)
            self.text("ROOM CLEAR  /  Enter 다음 방",420,574,26,CYAN)
        else:
            self.line(RIGHT-5,BOTTOM+6,RIGHT-5,BOTTOM+70,(186,184,174))
        mx,my=self.mouse
        self.line(mx-8,my,mx-3,my,CYAN);self.line(mx+3,my,mx+8,my,CYAN)
        self.line(mx,my-8,mx,my-3,CYAN);self.line(mx,my+3,mx,my+8,CYAN)
        p.draw_circle(mx,my,2,*CYAN,255,False)

    def panel(self,title,sub,lines,footer):
        self.rect(0,0,WIDTH,HEIGHT,(249,247,241),True,236)
        self.rect(242,147,1038,665,(255,254,249),True)
        self.rect(242,147,1038,665,(195,192,179))
        self.text(title,300,579,42,INK)
        self.text(sub,300,532,23,PURPLE)
        for i,line in enumerate(lines):self.text(line,300,465-i*43,20,INK)
        self.rect(300,185,980,231,(237,240,231),True)
        self.text(footer,325,207,20,CYAN)

    def title(self):
        self.text("01 / A GAME ON A BLANK PAGE",110,655,18,CYAN)
        self.text("Escape",105,555,66)
        self.text("Dimension",105,474,66)
        self.text("같은 종이. 다른 공간의 규칙.",111,397,26,MUTED)
        self.text("2D  좌우와 낙하",114,322,23,CYAN)
        self.text("3D  8방향 자유 이동",114,281,23,(152,115,27))
        self.text("4D  정지와 과거 위치",114,240,23,PURPLE)
        self.character_frame(7,880,399,285)
        self.sprite(4,1075,495,130)
        self.character_frame(12,1080,286,188)
        self.rect(505,185,775,243,CYAN,True)
        self.text("Enter  게임 시작",544,215,23,(255,255,255))
        self.text("Python + pico2d   ·   F1 조작 안내   ·   ESC 종료",407,126,16,MUTED)

    def draw(self):
        self.background()
        if self.args.smoke and self.args.smoke_scene=='motions':
            self.text('CHARACTER MOTION / FRAME PREVIEW',100,625,26,INK)
            rows=[('WALK', 'walk_player', [0,8,4,12]),
                  ('RELOAD', 'reload_player', [0,8,4,12]),
                  ('DEATH', 'death_both', [0,1,2,3])]
            for row,(label,atlas,frames) in enumerate(rows):
                y=510-row*145
                self.text(label,105,y,16,CYAN)
                for col,frame in enumerate(frames):
                    self.character_frame(frame,365+col*210,y,132,atlas=atlas)
            self.text('2D: LEFT / RIGHT     3D + 4D: EIGHT DIRECTIONS     AMMO: 6 / TOTAL 42',100,95,16,MUTED)
        elif self.args.smoke and self.args.smoke_scene=='directions':
            self.text('8-DIRECTION CHARACTER ATLAS',100,624,26,INK)
            self.text('PLAYER / MOUSE AIM     ·     ENEMY / TARGET TRACKING',100,590,16,MUTED)
            names=('E','NE','N','NW','W','SW','S','SE')
            for i in range(8):
                x=150+i*140
                self.character_frame(i,x,447,132)
                self.text(names[i],x-10,345,16,CYAN)
                self.character_frame(i+8,x,254,132)
            self.text('Python + pico2d / fixed camera, eight distinct facing images',100,95,18,MUTED)
        elif self.game.state=="title":self.title()
        else:
            self.world();self.hud()
            g=self.game
            if g.state=="dead" and g.death_finished:
                self.panel("페이지를 다시 펼칩니다",f"나이 +{g.last_age_cost}  /  현재 {g.age}세",[
                    "한 번의 피격으로 이번 시도가 끝났습니다.","해당 방 진입 전 상태와 탄약으로 돌아갑니다.",
                    f"다음 연속 사망의 기본 비용: +{2**g.streak}세","4D 종료 비용은 사망 비용과 별도로 적용됩니다."],"Enter  이 방 다시 도전")
            elif g.state=="over" and g.death_finished:
                self.panel("수명을 모두 사용했습니다",f"AGE {g.age}  /  40세 도달",[
                    f"도달한 방: {g.room_index+1} / {len(g.levels)}",f"전체 사망 {g.total_deaths}회   /   처치 {g.kills}회",
                    "지나친 시간 조작은 다음 시도를 어렵게 만듭니다.","다시 20세가 되어 첫 방부터 시작합니다."],"Enter  처음부터 다시 시작")
            elif g.state=="won":
                self.panel("ESCAPE COMPLETE",f"모든 방 섬멸 / 생존 나이 {g.age}세",[
                    f"방 {len(g.levels)}개 클리어   /   플레이 {int(g.elapsed//60)}분 {int(g.elapsed%60)}초",
                    f"발사 {g.shots}발   /   전체 사망 {g.total_deaths}회","이동 방향과 중력을 바꾸어 모든 페이지를 통과했습니다.",
                    "20세에 가까운 나이로 클리어해 보세요."],"Enter  새로운 플레이")
        if self.paused:self.panel("PAUSED","시간도 함께 멈춰 있습니다",["ESC를 누르면 이어서 플레이합니다.","F1을 누르면 조작과 규칙을 확인할 수 있습니다."],"ESC  계속하기")
        if self.help:
            self.panel("조작과 규칙","모든 화면은 2D로 구현됩니다",[
                "2D: A/D 좌우·SPACE 점프 / 3D·4D: WASD 이동",
                "마우스 조준 / 왼쪽 발사 / R 장전 (6발 / 합계 최대 42발)",
                "2/3/4: 모드 전환   ·   E 상자 집기 / Q 던지기",
                "4D: 휠·방향키로 과거 선택, Enter로 위치 이동",
                "4D 종료 +1세 / 연속 사망 +1, +2, +4… / 40세 종료",
                "빈 종이는 2D에서 높이, 3D에서 바닥입니다."],"F1 또는 ESC  닫기")

    def screenshot(self, filename):
        """Capture our SDL framebuffer. No OS/UI automation is used here."""
        import struct,zlib
        pixels=(ctypes.c_ubyte*(WIDTH*HEIGHT*4))()
        if SDL_RenderReadPixels(api.renderer,None,SDL_PIXELFORMAT_ARGB8888,pixels,WIDTH*4)!=0:
            raise RuntimeError("Framebuffer capture failed")
        raw=bytes(pixels)
        scan=bytearray()
        for row in range(HEIGHT):
            scan.append(0)
            for i in range(row*WIDTH*4,(row+1)*WIDTH*4,4):
                scan.extend((raw[i+2],raw[i+1],raw[i],255))
        def chunk(tag,data):return struct.pack('!I',len(data))+tag+data+struct.pack('!I',zlib.crc32(tag+data)&0xffffffff)
        png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',WIDTH,HEIGHT,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(scan))+chunk(b'IEND',b'')
        Path(filename).write_bytes(png)

    def run(self):
        previous=time.perf_counter();frames=0
        while self.running:
            now=time.perf_counter();dt=min(.05,now-previous);previous=now
            self.ui_time+=dt
            self.events()
            if not self.paused and not self.help and not self.args.smoke:
                mx=int(p.SDLK_d in self.keys)-int(p.SDLK_a in self.keys)
                my=int(p.SDLK_w in self.keys)-int(p.SDLK_s in self.keys)
                self.game.tick(dt,(mx,my),self.mouse,self.mouse_down)
            for event in self.game.events:
                sound=self.sounds.get(event)
                if sound and not self.muted:sound.play()
            self.game.events.clear()
            self.draw()
            if self.args.smoke and frames==3:
                if self.args.capture:self.screenshot(self.args.capture)
                self.running=False
            p.update_canvas();frames+=1
            time.sleep(.002)
        self.motion_atlases.clear()
        del self.atlas,self.characters
        p.close_canvas()

    def integration_test(self):
        """Test this app's real SDL event path, without controlling any other app."""
        import json
        from sdl2 import SDL_Event,SDL_PushEvent
        checks=[]
        def press(key):
            for kind in (p.SDL_KEYDOWN,p.SDL_KEYUP):
                event=SDL_Event();event.type=kind;event.key.type=kind
                event.key.repeat=0;event.key.keysym.sym=key
                SDL_PushEvent(ctypes.byref(event))
            self.events()
        def mouse(kind,x,y):
            event=SDL_Event();event.type=kind;event.button.type=kind
            event.button.button=1;event.button.x=int(x);event.button.y=int(HEIGHT-y)
            SDL_PushEvent(ctypes.byref(event));self.events()
        def check(name,condition):
            if not condition:raise AssertionError(name)
            checks.append(name)
        # The buttons and key handlers below are the same handlers as normal play.
        mouse(p.SDL_MOUSEBUTTONDOWN,640,213);mouse(p.SDL_MOUSEBUTTONUP,640,213)
        check('title_mouse_start',self.game.state=='playing')
        press(p.SDLK_SPACE)
        check('space_jumps_in_2d',self.game.player.vy>0)
        velocity=self.game.player.vy;press(p.SDLK_SPACE)
        check('space_cannot_double_jump',self.game.player.vy==velocity)
        for _ in range(60):self.game.tick(.02)
        check('jump_returns_to_floor',self.game.grounded)
        press(p.SDLK_3);check('key_3_free_mode',self.game.mode==3)
        press(p.SDLK_SPACE);check('space_does_not_jump_in_3d',self.game.player.vy==0)
        self.game.grace=100
        for _ in range(50):self.game.tick(.04,(1,.4))
        before=self.game.player.x
        press(p.SDLK_4);self.game.tick(.04)
        check('key_4_freezes_world',self.game.mode==4 and self.game.time_frozen)
        press(p.SDLK_SPACE);check('space_does_not_jump_in_4d',self.game.player.vy==0)
        press(p.SDLK_RIGHT);press(p.SDLK_RETURN)
        check('enter_rewind_returns_3d',self.game.mode==3 and self.game.age==21 and self.game.player.x<before)
        self.game.magazine=2;self.game.reserve=20
        press(p.SDLK_r)
        for _ in range(33):self.game.tick(.04)
        check('key_r_reload',self.game.magazine==6 and self.game.reserve==16)
        crate=self.game.crates[0];self.game.player.x=crate.x-55;self.game.player.y=crate.y
        press(p.SDLK_e);check('key_e_pickup',self.game.held is not None)
        press(p.SDLK_q);check('key_q_throw',self.game.held is None)
        mouse(p.SDL_MOUSEBUTTONDOWN,1050,420)
        # A synthetic event may not grant desktop focus, so test the firing handler itself.
        shot_aim=self.mouse
        self.game.tick(.04,aim=shot_aim,firing=True)
        mouse(p.SDL_MOUSEBUTTONUP,1050,420)
        if not (self.game.magazine==5 and shot_aim==(1050,420)):
            raise AssertionError(f'mouse_aim_and_fire: ammo={self.game.magazine}, aim={shot_aim}, state={self.game.state}, reload={self.game.reload_left}, cooldown={self.game.shot_cooldown}')
        check('mouse_aim_and_fire',True)
        press(p.SDLK_F1);check('f1_help',self.help)
        press(p.SDLK_ESCAPE);check('escape_closes_help',not self.help)
        press(p.SDLK_ESCAPE);check('escape_pause',self.paused)
        press(p.SDLK_ESCAPE);check('escape_resume',not self.paused)
        press(p.SDLK_m);check('m_mutes',self.muted)
        self.game.die();age=self.game.age;press(p.SDLK_RETURN)
        check('death_animation_blocks_early_retry',self.game.state=='dead')
        self.draw();check('death_first_frame',self.player_motion[0]=='death_both')
        for _ in range(45):self.game.tick(.02)
        self.draw()
        check('death_finishes_on_prone_frame',self.game.death_finished and self.player_motion[1]%4==3)
        press(p.SDLK_RETURN)
        check('enter_checkpoint_retry',self.game.state=='playing' and self.game.age==age and self.game.mode==2)
        self.game.age=39;press(p.SDLK_4);press(p.SDLK_3)
        check('age_40_game_over',self.game.state=='over')
        press(p.SDLK_RETURN);check('enter_full_restart',self.game.age==20 and self.game.room_index==0)
        # Follow real SDL mouse-motion events all the way through the renderer.
        self.game.player.x,self.game.player.y=620,340
        for mode in (2,3,4):
            press(p.SDLK_0+mode)
            for index in range(8):
                angle=index*math.pi/4
                x=round(620+math.cos(angle)*220)
                y=round(364+math.sin(angle)*220)
                event=SDL_Event();event.type=p.SDL_MOUSEMOTION
                event.motion.type=p.SDL_MOUSEMOTION;event.motion.x=x;event.motion.y=HEIGHT-y
                SDL_PushEvent(ctypes.byref(event));self.events();self.draw()
                expected=(4 if x<620 else 0) if mode==2 else index
                check(f'mouse_render_{mode}d_direction_{index}',self.player_facing==expected)
        self.game.set_mode(3)
        self.game.player.moving=True;self.game.player.walk_distance=0;self.draw()
        first=self.player_motion
        self.game.player.walk_distance=33;self.draw()
        check('walk_changes_leg_frame',first[0]=='walk_player' and self.player_motion!=first)
        self.game.player.moving=False;self.game.magazine=2;press(p.SDLK_r);self.draw()
        first=self.player_motion
        self.game.reload_left=RELOAD_DURATION*.4;self.draw()
        check('reload_changes_hand_frame',first[0]=='reload_player' and self.player_motion!=first)
        self.game.player.moving=True;self.game.player.walk_distance=0;self.draw()
        upper=self.player_layers['upper'];lower=self.player_layers['lower']
        self.game.player.walk_distance=33;self.draw()
        check('reload_walk_keeps_torso_and_changes_legs',
              self.player_layers['upper']==upper and self.player_layers['lower']!=lower
              and self.player_layers['lower'][0]=='walk_player')
        self.game.set_mode(2);self.game.reload_left=0;self.game.player.moving=False
        self.mouse=(900,550);self.draw()
        up=self.player_layers
        self.mouse=(900,200);self.draw()
        check('two_d_torso_aims_up_and_down_without_turning_legs',
              up['angle']>0 and self.player_layers['angle']<0 and up['lower']==self.player_layers['lower'])
        knife=type(self.game.player)(950,340,'knife',facing=4)
        self.actor(knife,(600,340))
        check('knife_uses_blade_art',self.last_enemy_art[0]=='knife_enemy')
        knife.alive=False;knife.death_elapsed=.8;self.actor(knife,(600,340))
        check('knife_death_keeps_blade_art',self.last_enemy_art[0]=='knife_enemy')
        self.game.start()
        self.draw()
        if self.args.capture:self.screenshot(self.args.capture)
        p.update_canvas()
        report={'status':'pass','checks':checks,'count':len(checks)}
        if self.args.test_report:Path(self.args.test_report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        self.motion_atlases.clear()
        del self.atlas,self.characters;p.close_canvas()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--smoke',action='store_true',help='Render a deterministic 4D frame and exit')
    parser.add_argument('--smoke-scene',choices=['title','2d','3d','4d','directions','motions'],default='4d')
    parser.add_argument('--smoke-room',type=int,choices=range(1,6),default=1)
    parser.add_argument('--capture',help='Save smoke-test framebuffer to PNG')
    parser.add_argument('--self-test',action='store_true',help='Run real SDL input integration tests')
    parser.add_argument('--test-report',help='Write input test report JSON')
    args=parser.parse_args()
    app=App(args)
    if args.self_test:app.integration_test()
    else:app.run()


if __name__=='__main__':
    try:main()
    except Exception:
        import traceback
        error=traceback.format_exc()
        print(error)
        if getattr(sys,'frozen',False):
            log=Path(sys.executable).with_name('error.log');log.write_text(error,encoding='utf-8')
            ctypes.windll.user32.MessageBoxW(None,'실행 중 문제가 발생했습니다. 같은 폴더의 error.log를 확인하세요.','Escape Dimension',0x10)
        raise
