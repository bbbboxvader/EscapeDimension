import sys
import unittest
from math import hypot
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Game, Actor, MAX_AMMO, MAGAZINE_SIZE, DEATH_DURATION


def arena():
    g=Game();g.start();g.crates=[];g.obstacles=[];g.ammo_pickups=[]
    g.enemies=[Actor(1100,176,'sentry',timer=100)]
    g.grace=100
    return g


class CombatChanges(unittest.TestCase):
    def test_six_loaded_and_42_total_at_start_and_restart(self):
        g=arena()
        self.assertEqual((g.magazine,g.reserve,g.total_ammo),(6,36,42))
        for _ in range(6):
            g.shot_cooldown=0;self.assertTrue(g.shoot((900,300)))
        self.assertFalse(g.shoot((900,300)))
        g.start();self.assertEqual(g.total_ammo,42)

    def test_full_ammo_does_not_consume_pickup(self):
        g=arena();g.ammo_pickups=[[g.player.x,g.player.y]]
        g.tick(.02)
        self.assertEqual(g.total_ammo,MAX_AMMO)
        self.assertEqual(len(g.ammo_pickups),1)

    def test_partial_pickup_caps_total_at_42(self):
        g=arena();g.magazine=2;g.reserve=35
        g.ammo_pickups=[[g.player.x,g.player.y]];g.tick(.02)
        self.assertEqual((g.magazine,g.reserve,g.total_ammo),(2,40,42))
        self.assertEqual(g.ammo_pickups,[])
        self.assertTrue(g.reload())
        for _ in range(70):g.tick(.02)
        self.assertEqual((g.magazine,g.reserve),(6,36))

    def test_two_d_aims_up_and_down_while_facing_left_or_right(self):
        g=arena()
        for x,side in ((900,0),(100,4)):
            for y in (170,600):
                g.shot_cooldown=0;g.shoot((x,y))
                if y>g.player.y+24:
                    self.assertGreater(g.bullets[-1].vy,0)
                else:
                    self.assertLess(g.bullets[-1].vy,0)
                self.assertEqual(g.player.facing,side)

    def test_free_modes_can_shoot_vertically(self):
        for mode in (3,4):
            g=arena();g.set_mode(mode)
            g.shoot((g.player.x,600))
            self.assertAlmostEqual(g.bullets[-1].vx,0)
            self.assertGreater(g.bullets[-1].vy,0)
            self.assertEqual(g.player.facing,2)

    def test_enemy_bullet_speed_increases_with_room(self):
        for index in range(5):
            g=arena();g.room_index=index;g.grace=0
            g.enemies=[Actor(900,176,'sentry',timer=0,aim_x=155,aim_y=200,winding=True)]
            g.update_enemies(.01)
            bullet=g.bullets[-1]
            self.assertAlmostEqual(hypot(bullet.vx,bullet.vy),320+25*index)
            self.assertIn(g.enemies[0].facing,(0,4))

    def test_walk_phase_advances_only_with_actual_ground_motion(self):
        g=arena();before=g.player.walk_distance;g.tick(.04,(1,0))
        self.assertGreater(g.player.walk_distance,before)
        self.assertTrue(g.player.moving)
        before=g.player.walk_distance;g.tick(.04)
        self.assertEqual(g.player.walk_distance,before)
        self.assertFalse(g.player.moving)
        g.player.y=400;g.tick(.04)
        self.assertFalse(g.player.moving)

    def test_death_animation_advances_without_age_or_world_progress(self):
        g=arena();g.die();age=g.age;time=g.world_time
        self.assertFalse(g.death_finished)
        for _ in range(45):g.tick(.02)
        self.assertTrue(g.death_finished)
        self.assertFalse(g.player.alive)
        self.assertEqual((g.age,g.world_time),(age,time))

    def test_enemy_death_motion_freezes_with_four_d_world(self):
        g=arena();g.set_mode(4);enemy=g.enemies[0];g.kill(enemy)
        for _ in range(20):g.tick(.02)
        self.assertEqual(enemy.death_elapsed,0)
        g.tick(.04,(1,0))
        self.assertGreater(enemy.death_elapsed,0)

    def test_reload_clock_and_motion_progress_freeze_in_four_d(self):
        g=arena();g.magazine=2;g.reload();g.set_mode(4)
        before=g.reload_left;g.tick(.05)
        self.assertEqual(g.reload_left,before)
        g.tick(.05,(1,0));self.assertLess(g.reload_left,before)
