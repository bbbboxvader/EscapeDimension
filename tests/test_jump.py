import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Game, Actor, Crate, BOTTOM, TOP, PLAYER_HALF, JUMP_SPEED


def arena():
    game=Game();game.start();game.crates=[];game.obstacles=[];game.ammo_pickups=[]
    game.enemies=[Actor(1100,176,'sentry',timer=100)]
    game.grace=100
    return game


class JumpTests(unittest.TestCase):
    def test_ground_jump_rises_and_lands_without_air_jump(self):
        game=arena();start=game.player.y
        self.assertTrue(game.grounded)
        self.assertTrue(game.jump())
        self.assertEqual(game.player.vy,JUMP_SPEED)
        self.assertFalse(game.jump())
        peak=start
        for _ in range(60):
            game.tick(.02)
            peak=max(peak,game.player.y)
        self.assertGreater(peak,start+85)
        self.assertEqual(game.player.y,start)
        self.assertTrue(game.grounded)
        self.assertTrue(game.jump())

    def test_jump_from_crate_and_shelf(self):
        for support in ('crate','shelf'):
            with self.subTest(support=support):
                game=arena();game.player.x=500
                if support=='crate':
                    game.crates=[Crate(500,BOTTOM+23)]
                    top=game.crates[0].box[3]
                else:
                    game.obstacles=[(450,300,550,316)]
                    top=316
                game.player.y=top+PLAYER_HALF
                self.assertTrue(game.jump())
                for _ in range(60):game.tick(.02)
                self.assertAlmostEqual(game.player.y,top+PLAYER_HALF)
                self.assertTrue(game.grounded)

    def test_no_jump_in_free_modes_or_when_dead(self):
        for mode in (3,4):
            game=arena();game.set_mode(mode)
            before=game.player.y
            self.assertFalse(game.jump())
            game.tick(.05)
            self.assertEqual(game.player.y,before)
        game=arena();game.die()
        self.assertFalse(game.jump())

    def test_no_jump_after_walking_off_a_platform(self):
        game=arena();game.obstacles=[(450,300,550,316)]
        game.player.x=570;game.player.y=316+PLAYER_HALF
        self.assertFalse(game.grounded)
        self.assertFalse(game.jump())

    def test_ceiling_hit_cancels_upward_velocity(self):
        game=arena();game.obstacles=[(100,280,210,296)]
        game.jump()
        for _ in range(40):
            game.tick(.02)
            self.assertLessEqual(game.player.box[3],280)
        self.assertTrue(game.grounded)

    def test_top_boundary_does_not_leave_player_hanging(self):
        game=arena();top=TOP-90
        game.obstacles=[(100,top-16,210,top)]
        game.player.y=top+PLAYER_HALF
        self.assertTrue(game.jump())
        hit_ceiling=False
        for _ in range(60):
            game.tick(.02)
            if game.player.y==TOP-48:
                hit_ceiling=True
                self.assertEqual(game.player.vy,0)
        self.assertTrue(hit_ceiling)
        self.assertAlmostEqual(game.player.y,top+PLAYER_HALF)

    def test_free_mode_switch_cancels_jump_velocity(self):
        game=arena();game.jump();game.tick(.05)
        game.set_mode(3);height=game.player.y
        game.tick(.05)
        self.assertEqual((game.player.y,game.player.vy),(height,0))
