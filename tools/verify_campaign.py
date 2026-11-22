"""Exercise real renderer/input paths for large maps, bosses and wall breaches."""
from pathlib import Path
import argparse,ctypes,json,sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from main import App
from core import Actor,Grenade,BOSS_KINDS
import pico2d as p
from sdl2 import SDL_Event,SDL_PushEvent

parser=argparse.ArgumentParser()
parser.add_argument('--output',default=str(root/'verification/campaign'))
args=parser.parse_args()
out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
app=App(argparse.Namespace(smoke=True,smoke_scene='title',smoke_room=1,capture=None))
checks=[]
def check(name,condition):
    if not condition:raise AssertionError(name)
    checks.append(name)
def key(code):
    for kind in (p.SDL_KEYDOWN,p.SDL_KEYUP):
        e=SDL_Event();e.type=kind;e.key.type=kind;e.key.keysym.sym=code
        SDL_PushEvent(ctypes.byref(e))
    app.events()
def click(x,y,kind=p.SDL_MOUSEBUTTONDOWN):
    e=SDL_Event();e.type=kind;e.button.type=kind;e.button.button=1
    e.button.x=round(x);e.button.y=800-round(y)
    SDL_PushEvent(ctypes.byref(e));app.events()
def chapter(index):
    app.game.start();app.game.room_index=index;app.game.load_room();app.game.set_mode(3)
    app.game.grace=100;app.game.hint_left=0

try:
    key(p.SDLK_LEFT);key(p.SDLK_RETURN)
    check('title_selects_chapter_12',app.game.room_index==11 and app.game.state=='playing')
    for i in range(12):
        chapter(i);g=app.game
        g.player.x=min(g.right-250,1500);g.player.y=480
        before=(g.player.x,g.player.y,tuple((e.x,e.y,e.hp) for e in g.enemies))
        app.draw()
        check(f'chapter_{i+1:02d}_renders_without_mutating_world',
              before==(g.player.x,g.player.y,tuple((e.x,e.y,e.hp) for e in g.enemies)) and app.game is g)
    for index,name in [(5,'chapter-06-midboss'),(11,'chapter-12-finalboss')]:
        chapter(index);g=app.game;boss=next(e for e in g.enemies if e.kind in BOSS_KINDS)
        g.player.x,g.player.y=boss.x-330,280;g.grace=0
        boss.alerted=True;boss.timer=.85
        if g.command_window:g.laser_clock=.01
        g.tick(.02)
        app.mouse=(900,250);app.draw();app.screenshot(str(out/(name+'.png')))
        check(name+'_visible_with_scrolled_camera',app.camera.x>0 and (bool(g.lasers) if g.command_window else boss.winding))
    chapter(1);g=app.game;enemy=next(e for e in g.enemies if e.kind=='grenadier')
    g.player.x,g.player.y=enemy.x-210,480
    app.mouse=(900,450);app.draw();app.screenshot(str(out/'grenadier.png'))
    check('grenadier_atlas_loaded',app.special_enemies.w>0 and app.special_enemies.h>0)
    chapter(7);g=app.game;g.player.x,g.player.y=760,300
    enemy=next(e for e in g.enemies if e.kind=='grenadier')
    before=len(g.obstacles);app.draw();app.screenshot(str(out/'wall-before.png'))
    g.launch_grenade(enemy,(760,320))
    for _ in range(8):g.update_grenades(.05)
    app.draw();app.screenshot(str(out/'grenade-flight.png'))
    for _ in range(40):
        g.update_grenades(.025)
        if g.blasts:break
    app.draw();app.screenshot(str(out/'wall-after.png'))
    check('grenade_wall_breach_renders',len(g.obstacles)<before and bool(g.blasts) and bool(g.fragments))
    chapter(0);g=app.game;g.crates=[];g.obstacles=[];g.ammo_pickups=[]
    g.player=Actor(2000,300);g.enemies=[Actor(2240,300,'sentry',timer=100)]
    app.draw()
    check('camera_scrolls_past_original_room',app.camera.x>1100)
    target=app.camera.to_screen(2240,324)
    click(*target)
    aim=app.world_mouse
    check('mouse_screen_to_world_after_scroll',abs(aim[0]-2240)<1 and abs(aim[1]-324)<1)
    g.tick(.04,aim=aim,firing=app.mouse_down)
    click(*target,kind=p.SDL_MOUSEBUTTONUP)
    for _ in range(15):g.tick(.025)
    check('scrolled_mouse_shot_hits_actual_world_target',not g.enemies[0].alive)
    g.player.x=1900;g.player.y=300;app.draw()
    g.history.clear();g.history.extend([(0.,1500.,300.),(1.,1700.,300.),(2.,1900.,300.)]);g.world_time=2
    key(p.SDLK_4)
    points=g.rewind_points();index=len(points)-1
    point=app.camera.to_screen(points[index][1],points[index][2])
    click(*point);click(*point,kind=p.SDL_MOUSEBUTTONUP)
    check('scrolled_ghost_click_selects_correct_past_position',g.selected==index)
    key(p.SDLK_RETURN)
    check('scrolled_rewind_returns_to_world_position',g.mode==3 and g.player.x==points[index][1])
    chapter(0);app.game.set_mode(2);app.draw();app.screenshot(str(out/'chapter-01-entry.png'))
    report={'status':'pass','count':len(checks),'checks':checks,'chapters':12}
    (out/'input-and-render.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':'pass','count':len(checks),'chapters':12}))
finally:
    app.motion_atlases.clear();del app.atlas,app.characters,app.special_enemies,app.elite_gunner,app.commander_art
    p.close_canvas()
