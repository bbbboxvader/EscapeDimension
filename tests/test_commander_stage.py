"""Final-window objective and readable four-sided laser combat."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Game,Actor,Bullet,Grenade
from hazards import LaserBeam
from camera import Camera

def final_stage():
    g=Game();g.room_index=11;g.load_room();g.grace=0;g.laser_clock=100
    return g

class CommanderStageTests(unittest.TestCase):
    def test_window_has_36_hit_points_and_commander_stays_behind_it(self):
        g=final_stage();boss=g.enemies[0];position=boss.x,boss.y
        for _ in range(60):g.tick(.02,(1,0))
        self.assertEqual(g.command_window.hp,36)
        self.assertEqual(position,(boss.x,boss.y))
        self.assertFalse(g.bullets);self.assertFalse(g.grenades)

    def test_player_bullet_chips_window_once_and_is_consumed(self):
        g=final_stage();x=(g.command_window.box[0]+g.command_window.box[2])/2
        g.bullets=[Bullet(x,500,0,2000,'player')]
        g.update_bullets(.05)
        self.assertEqual(g.command_window.hp,35)
        self.assertEqual(g.enemies[0].hp,35)
        self.assertFalse(g.bullets)
        self.assertIn('glass_hit',g.events)

    def test_glass_damage_states_accumulate_and_finish_shattered(self):
        g=final_stage();w=g.command_window
        self.assertEqual(w.damage_stage,0)
        g.damage_window(12);self.assertEqual(w.damage_stage,1)
        g.damage_window(12);self.assertEqual(w.damage_stage,2)
        g.damage_window(12);self.assertEqual(w.damage_stage,3)

    def test_explosion_and_crate_damage_do_not_bypass_window_objective(self):
        g=final_stage();g.grace=100;w=g.command_window;boss=g.enemies[0]
        g.explode(Grenade(boss.x,boss.y,0,0,radius=200))
        g.damage_enemy(boss,99)
        self.assertEqual(w.hp,36);self.assertTrue(boss.alive)

    def test_warning_line_is_safe_until_beam_activates(self):
        g=final_stage();x,y=g.player.x,g.player.y
        g.lasers=[LaserBeam(x,545,x,157,'top',warning=1,age=.8)]
        for _ in range(3):g.tick(.05)
        self.assertEqual(g.state,'playing')
        g.tick(.05);g.tick(.01)
        self.assertEqual(g.state,'dead')

    def test_all_four_sides_emit_in_first_four_waves(self):
        g=final_stage()
        for _ in range(4):g.spawn_laser_wave()
        self.assertEqual({l.side for l in g.lasers},{'left','right','top','bottom'})
        self.assertTrue(all(not l.active for l in g.lasers))

    def test_window_damage_adds_crossfire_and_third_phase(self):
        for damage,phase,count in [(0,1,1),(12,2,2),(24,3,4)]:
            g=final_stage();g.damage_window(damage);g.update_command_stage(.01)
            self.assertEqual(g.enemies[0].phase,phase)
            g.spawn_laser_wave();self.assertEqual(len(g.lasers),count)
            if phase==3:self.assertEqual({l.side for l in g.lasers},{'left','right','top','bottom'})

    def test_finished_beams_expire(self):
        g=final_stage();g.lasers=[LaserBeam(2000,450,3100,450,'left',age=1.59,warning=1,duration=.6)]
        g.update_command_stage(.02)
        self.assertFalse(g.lasers)

    def test_four_d_freezes_laser_warning_clock_and_glass_flash(self):
        g=final_stage();g.damage_window();g.lasers=[LaserBeam(2000,450,3100,450,'left',warning=2)]
        g.set_mode(4);before=(g.lasers[0].age,g.laser_clock,g.command_window.hit_flash)
        for _ in range(10):g.tick(.02)
        self.assertEqual(before,(g.lasers[0].age,g.laser_clock,g.command_window.hit_flash))
        self.assertLess(g.time_left,10)
        g.tick(.04,(1,0));self.assertGreater(g.lasers[0].age,before[0])

    def test_rewind_cannot_land_in_an_active_laser(self):
        g=final_stage();x,y=g.player.x,g.player.y
        g.lasers=[LaserBeam(x,545,x,157,'top',warning=1,age=1.2)]
        self.assertFalse(g.safe_position(x,y))
        self.assertTrue(g.safe_position(x+80,y))

    def test_final_shot_stops_all_lasers_and_unlocks_ending(self):
        g=final_stage();g.lasers=[LaserBeam(2000,450,3100,450,'left',age=1.2)]
        g.damage_window(36);self.assertFalse(g.lasers)
        self.assertFalse(g.enemies[0].alive)
        g.tick(.01);self.assertTrue(g.clear)
        self.assertTrue(g.next_room());self.assertEqual(g.state,'won')

    def test_retry_repairs_window_and_resets_all_laser_patterns(self):
        g=final_stage();g.damage_window(20);g.spawn_laser_wave();g.die();g.retry()
        self.assertEqual(g.command_window.hp,36)
        self.assertFalse(g.lasers);self.assertEqual(g.laser_cycle,0)
        self.assertEqual(g.mode,3)

    def test_player_cannot_walk_into_control_room(self):
        g=final_stage();g.player.x=500;g.player.y=1100
        g.move_actor(g.player,0,0,.02)
        l,b,r,t=g.movement_bounds(g.player)
        self.assertGreaterEqual(g.player.x,l+16)
        self.assertLessEqual(g.player.box[3],g.command_window.box[1])

    def test_camera_is_locked_to_arena_for_all_player_positions(self):
        g=final_stage();c=Camera();arena=g.room['arena']
        c.follow(g.player,g.bounds,arena);before=c.x,c.y
        g.player.x+=350;g.player.y+=150;c.follow(g.player,g.bounds,arena)
        self.assertEqual(before,(c.x,c.y))

class EliteSoldierTests(unittest.TestCase):
    def test_machinegun_has_a_telegraph_and_locks_aim_before_firing(self):
        g=Game();g.start();g.grace=0;g.set_mode(3);e=Actor(800,300,'midboss',timer=.8)
        g.player=Actor(400,300);g.enemies=[e]
        g.update_boss(e,.02,400);self.assertTrue(e.winding);self.assertFalse(g.bullets)
        before=e.aim_x,e.aim_y;e.timer=.25;g.player.y=480
        g.update_boss(e,.02,400);self.assertEqual(before,(e.aim_x,e.aim_y))
        e.timer=0;g.update_boss(e,.02,400)
        self.assertTrue(g.bullets);self.assertEqual(g.bullets[0].style,'machinegun')

    def test_machinegun_burst_freezes_in_four_d(self):
        g=Game();g.start();g.grace=0;g.set_mode(3);g.crates=[];g.obstacles=[]
        e=Actor(800,300,'midboss',timer=0,aim_x=400,aim_y=324);g.enemies=[e];g.player=Actor(400,300)
        g.update_boss(e,.02,400);g.set_mode(4)
        before=e.burst_left,e.burst_delay,e.timer
        for _ in range(10):g.tick(.02)
        self.assertEqual(before,(e.burst_left,e.burst_delay,e.timer))

if __name__=='__main__':unittest.main()
