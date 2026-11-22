"""Verify real SDL aiming, machine-gun art and all glass/laser render states."""
from pathlib import Path
import argparse,ctypes,json,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from main import App
import pico2d as p
from sdl2 import SDL_Event,SDL_PushEvent

parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(root/'verification/boss-fights'))
out=Path(parser.parse_args().output);out.mkdir(parents=True,exist_ok=True)
app=App(argparse.Namespace(smoke=True,smoke_scene='title',smoke_room=1,capture=None))
checks=[]
def check(name,condition):
    if not condition:raise AssertionError(name)
    checks.append(name)
def chapter(index):
    app.game.start();app.game.room_index=index;app.game.load_room();app.game.set_mode(3)
def click(x,y,kind):
    e=SDL_Event();e.type=kind;e.button.type=kind;e.button.button=1;e.button.x=round(x);e.button.y=800-round(y)
    SDL_PushEvent(ctypes.byref(e));app.events()
def key(code):
    for kind in (p.SDL_KEYDOWN,p.SDL_KEYUP):
        e=SDL_Event();e.type=kind;e.key.type=kind;e.key.keysym.sym=code
        SDL_PushEvent(ctypes.byref(e))
    app.events()
def capture(name):
    app.draw();app.screenshot(str(out/(name+'.png')))
try:
    chapter(5);g=app.game;boss=next(e for e in g.enemies if e.kind=='midboss')
    g.enemies=[boss];g.grace=0;g.player.x,g.player.y=boss.x-350,280
    boss.timer=0;boss.aim_x,boss.aim_y=g.player.x,g.player.y+24
    g.update_boss(boss,.02,350);app.ui_time=0
    capture('elite-machinegun')
    check('elite_uses_machinegun_burst',boss.burst_left>0 and any(b.style=='machinegun' for b in g.bullets))
    check('machinegun_does_not_launch_grenades',not g.grenades)
    chapter(11);g=app.game;g.grace=100
    g.damage_window(24);g.update_command_stage(.01);g.spawn_laser_wave()
    l,b,r,t=g.movement_bounds()
    g.player.x,g.player.y=next((x,y) for x in range(int(l+35),int(r-35),20) for y in range(int(b+25),int(t-50),15)
        if not any(g.overlap((x-15,y-22,x+15,y+48),beam.box) for beam in g.lasers))
    g.grace=0
    check('final_phase_emits_from_all_four_sides',{l.side for l in g.lasers}=={'left','right','top','bottom'})
    g.update_command_stage(.65);capture('commander-laser-warning')
    check('laser_warning_is_visually_distinct',all(not l.active for l in g.lasers))
    g.update_command_stage(.45);capture('commander-lasers-active')
    check('lasers_switch_from_warning_to_active',all(l.active for l in g.lasers))
    check('four_direction_crossfire_has_a_safe_space',g.state=='playing')
    chapter(11);g=app.game;g.grace=100
    for _ in range(20):g.tick(.025,(1,0))
    g.spawn_laser_wave();key(p.SDLK_4)
    before=[l.age for l in g.lasers];g.tick(.05);capture('commander-time-freeze')
    check('laser_age_freezes_in_actual_four_d_input',before==[l.age for l in g.lasers])
    chapter(11);g=app.game;g.grace=100
    capture('commander-glass-intact')
    l,b,r,t=g.command_window.box;aim=app.camera.to_screen((l+r)/2,(b+t)/2)
    click(*aim,p.SDL_MOUSEBUTTONDOWN)
    seen={0};previous=g.command_window.hp
    # Isolate the shoot/reload/glass input path; laser damage is tested separately.
    for frame in range(1600):
        if not g.magazine and g.reload_left<=0:g.reload()
        g.tick(.025,aim=app.world_mouse,firing=app.mouse_down)
        check_delta=previous-g.command_window.hp
        if check_delta:check('each_window_hit_removes_one_point_'+str(g.command_window.hp),check_delta==1)
        previous=g.command_window.hp
        state=g.command_window.damage_stage
        if state not in seen:
            seen.add(state);capture('commander-glass-'+str(state))
        if not g.command_window.hp:break
    click(*aim,p.SDL_MOUSEBUTTONUP)
    check('actual_mouse_fire_and_reload_break_window',g.command_window.hp==0 and g.shots>=36)
    check('all_four_glass_render_states_used',seen=={0,1,2,3})
    check('broken_window_stops_all_lasers',not g.lasers and not g.enemies[0].alive)
    key(p.SDLK_RETURN);check('enter_after_glass_break_finishes_campaign',g.state=='won')
    report={'status':'pass','count':len(checks),'checks':checks}
    (out/'boss-input-and-render.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'status':'pass','count':len(checks)}))
finally:
    app.motion_atlases.clear()
    del app.atlas,app.characters,app.special_enemies,app.elite_gunner,app.commander_art
    p.close_canvas()
