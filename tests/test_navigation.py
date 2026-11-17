import sys
import unittest
from math import hypot
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Game, Actor, Crate, LEFT, RIGHT, BOTTOM, TOP


def arena(kind='knife'):
    g=Game();g.start();g.crates=[];g.obstacles=[];g.ammo_pickups=[]
    g.player=Actor(950,340)
    g.enemies=[Actor(250,340,kind,timer=100)]
    g.grace=0;g.set_mode(3)
    return g


class PursuitTests(unittest.TestCase):
    def test_u_shaped_cover_requires_first_moving_away_from_player(self):
        g=arena();e=g.enemies[0];e.x,e.y=530,380
        g.player.x,g.player.y=1050,380
        g.obstacles=[(650,220,670,540),(380,520,670,540),(380,220,670,240)]
        leftmost=e.x
        for _ in range(600):
            g.tick(.02);leftmost=min(leftmost,e.x)
            self.assertFalse(any(g.overlap(e.box,r) for r in g.obstacles))
            if e.x>760:break
        self.assertLess(leftmost,380)
        self.assertGreater(e.x,760)

    def test_knife_is_faster_than_player_and_does_not_fire(self):
        g=arena();e=g.enemies[0];x=e.x
        g.tick(.05)
        self.assertGreater(e.x-x,g.speed*.05*1.6)
        self.assertEqual(g.bullets,[])

    def test_chasers_route_around_full_body_wall_without_overlap(self):
        for kind in ('knife','hunter','sentry'):
            with self.subTest(kind=kind):
                g=arena(kind);g.obstacles=[(500,220,560,490)]
                e=g.enemies[0];highest=e.y
                for _ in range(400):
                    g.tick(.02)
                    self.assertFalse(g.overlap(e.box,g.obstacles[0]))
                    highest=max(highest,e.y)
                    if e.x>600 or (kind=='sentry' and not g.blocked(e.x,e.y+24,g.player.x,g.player.y+24)
                                   and hypot(e.x-g.player.x,e.y-g.player.y)<=480):break
                if kind=='sentry':
                    self.assertFalse(g.blocked(e.x,e.y+24,g.player.x,g.player.y+24))
                    self.assertLessEqual(hypot(e.x-g.player.x,e.y-g.player.y),480)
                else:
                    self.assertGreater(e.x,600)
                self.assertGreater(highest,510)

    def test_navigation_replans_after_a_crate_moves(self):
        g=arena();e=g.enemies[0]
        g.obstacles=[(500,220,560,490)]
        g.tick(.02)
        revision=g._nav_revision
        g.crates=[Crate(650,550)]
        g.tick(.02)
        self.assertGreater(g._nav_revision,revision)
        for _ in range(200):
            g.tick(.02)
            self.assertFalse(g.overlap(e.box,g.crates[0].box))
            if e.x>600:break
        self.assertGreater(e.x,600)

    def test_inaccessible_wall_does_not_cause_clipping(self):
        g=arena();e=g.enemies[0];g.obstacles=[(500,BOTTOM,560,TOP)]
        for _ in range(50):g.tick(.02)
        self.assertLess(e.x,485)
        self.assertFalse(g.overlap(e.box,g.obstacles[0]))

    def test_knife_jumps_over_low_cover_in_2d(self):
        g=arena();g.set_mode(2);g.player=Actor(900,BOTTOM+22)
        e=g.enemies[0];e.x,e.y=250,BOTTOM+22
        g.obstacles=[(410,BOTTOM,470,BOTTOM+55)]
        peak=e.y
        for _ in range(180):
            g.tick(.02);peak=max(peak,e.y)
            self.assertFalse(g.overlap(e.box,g.obstacles[0]))
            if e.x>520:break
        self.assertGreater(e.x,520)
        self.assertGreater(peak,BOTTOM+75)

    def test_knife_descends_from_a_platform_to_player_below(self):
        g=arena();g.set_mode(2);g.player=Actor(600,BOTTOM+22)
        g.obstacles=[(480,330,720,346)]
        e=g.enemies[0];e.x,e.y=600,368
        for _ in range(180):
            g.tick(.02)
            if e.y<240:break
        self.assertLess(e.y,240)

    def test_fast_chaser_and_its_route_freeze_in_four_d(self):
        g=arena();g.set_mode(4);e=g.enemies[0]
        before=e.x,e.y,e.walk_distance,e.nav_left
        for _ in range(20):g.tick(.02)
        self.assertEqual(before,(e.x,e.y,e.walk_distance,e.nav_left))
        g.tick(.02,(1,0))
        self.assertGreater(e.x,before[0])

    def test_knife_attack_is_blocked_by_cover(self):
        g=arena();g.player=Actor(540,340);e=g.enemies[0];e.x=500
        g.obstacles=[(518,300,522,410)]
        g.update_enemies(.001)
        self.assertEqual(g.state,'playing')
        self.assertFalse(g.overlap(e.box,g.obstacles[0]))
        g.obstacles=[];g.update_enemies(.001)
        self.assertEqual(g.state,'dead')
