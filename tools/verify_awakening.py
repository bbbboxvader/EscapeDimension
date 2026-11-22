"""Exercise real SDL controls for awakening, view rotation and gravity weapons."""
from pathlib import Path
import argparse,ctypes,json,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from main import App
from core import Actor,Grenade,ThrownKnife
from space import turn_point
import pico2d as p
from sdl2 import SDL_Event,SDL_PushEvent

parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(root/'verification/awakening'))
out=Path(parser.parse_args().output);out.mkdir(parents=True,exist_ok=True)
app=App(argparse.Namespace(smoke=True,smoke_scene='title',smoke_room=1,capture=None))
checks=[]
def check(name,value):
    if not value:raise AssertionError(name)
    checks.append(name)
def key(code):
    for kind in (p.SDL_KEYDOWN,p.SDL_KEYUP):
        e=SDL_Event();e.type=kind;e.key.type=kind;e.key.keysym.sym=code;SDL_PushEvent(ctypes.byref(e))
    app.events()
def capture(name):
    app.draw();app.screenshot(str(out/(name+'.png')))
def chapter(index):
    app.game.start();app.game.room_index=index;app.game.load_room();app.game.grace=100
    app.game.set_mode(3);app.draw()
try:
    # Isolate the input/kill/unlock path; normal-damage survival is checked separately.
    chapter(5);g=app.game;boss=next(e for e in g.enemies if e.kind=='midboss')
    g.enemies=[boss];boss.hp=1;g.obstacles=[];g.crates=[]
    g.player.x,g.player.y=boss.x-200,boss.y;app.draw()
    app.mouse=app.camera.to_screen(boss.x,boss.y+25)
    for _ in range(40):
        g.tick(.02,aim=app.world_mouse,firing=True)
        if g.clear:break
    check('actual_bullet_clear_unlocks_awakening',g.clear and g.awakened)
    capture('awakening-unlocked')
    key(p.SDLK_4);key(p.SDLK_x)
    check('x_rotates_clockwise_only_in_four_d',g.view_turn==1 and g.mode==4)
    key(p.SDLK_z);check('z_reverses_rotation',g.view_turn==0)
    key(p.SDLK_3);key(p.SDLK_x);check('rotation_is_locked_outside_four_d',g.view_turn==0)
    key(p.SDLK_f);check('f_throws_single_knife',not g.knife_owned and len(g.knives)==1)
    key(p.SDLK_f);check('cannot_throw_second_knife',len(g.knives)==1)
    g.knives[0].x,g.knives[0].y=g.player.x+25,g.player.y
    key(p.SDLK_e);check('e_recovers_knife',g.knife_owned and not g.knives)
    chapter(11);g=app.game;g.damage_window(24);g.update_command_stage(.01);g.spawn_laser_wave()
    g.launch_grenade(g.enemies[0],(g.player.x-160,g.player.y))
    g.launch_grenade(g.enemies[0],(g.player.x+160,g.player.y))
    check('phase_three_has_seven_warning_beams',len(g.lasers)==7)
    capture('commander-barrage-warning')
    for laser in g.lasers:laser.age=laser.warning+.08
    # Find an actual safe cell, then exercise normal active-beam damage there.
    l,b,r,t=g.movement_bounds()
    safe=next((x,y) for x in range(int(l+35),int(r-35),20) for y in range(int(b+25),int(t-50),15)
              if not any(g.overlap((x-15,y-22,x+15,y+48),laser.box) for laser in g.lasers))
    g.player.x,g.player.y=safe;g.grace=0;g.bomb_clock=100;g.laser_clock=100
    g.update_command_stage(.01)
    check('dense_active_pattern_has_a_safe_cell',g.state=='playing')
    capture('commander-barrage-active')
    chapter(11);g=app.game
    g.grenades=[Grenade(2544,300,0,0,fuse=3,flight_time=10,source=g.enemies[0])]
    key(p.SDLK_4);key(p.SDLK_x);g.tick(.01)
    before=(g.grenades[0].fuse,g.grenades[0].age,g.command_window.hp)
    capture('rotation-90')
    x,y=app.camera.to_screen(2544,590);wx,wy=app.camera.to_world(x,y)
    check('rotated_mouse_inverse_matches_window',abs(wx-2544)<.001 and abs(wy-590)<.001)
    check('all_final_arena_visible_at_90_degrees',app.camera.scale<1)
    for _ in range(10):g.tick(.02)
    check('rotated_four_d_still_freezes_bomb',before==(g.grenades[0].fuse,g.grenades[0].age,g.command_window.hp))
    key(p.SDLK_x);capture('rotation-180-frozen')
    check('two_turns_put_window_below_bomb',g.view_turn==2 and g.grenades[0].redirected)
    g.player.x=2900;key(p.SDLK_2)
    for _ in range(80):
        g.tick(.02)
        if g.command_window.hp<36:break
    check('two_d_gravity_counter_bomb_hits_glass',g.command_window.hp==30)
    check('counter_bomb_does_not_consume_ammo',g.total_ammo==42)
    capture('gravity-bomb-glass-hit')
    # Verify drawing is read-only in the fully rotated scene.
    before=(g.player.x,g.player.y,tuple(g.obstacles),g.command_window.box,g.view_turn)
    app.draw();app.draw()
    check('rotated_render_keeps_world_geometry',before==(g.player.x,g.player.y,tuple(g.obstacles),g.command_window.box,g.view_turn))
    chapter(6);g=app.game;g.crates=[];g.obstacles=[];g.enemies=[Actor(800,176,'sentry',timer=100)]
    g.player.x,g.player.y=600,176;g.set_mode(2)
    g.knives=[ThrownKnife(800,450)];g.knife_owned=False
    for _ in range(60):
        g.tick(.02)
        if not g.enemies[0].alive:break
    check('knife_kills_after_long_gravity_fall',not g.enemies[0].alive)
    capture('knife-gravity-attack')
    report={'status':'pass','count':len(checks),'checks':checks,
            'scope':'Isolated SDL control/render checks; survival uses normal-damage simulation tests.'}
    (out/'input-and-render.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'status':'pass','count':len(checks)}))
finally:
    app.motion_atlases.clear()
    del app.atlas,app.characters,app.special_enemies,app.elite_gunner,app.commander_art
    p.close_canvas()
