import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Game, Actor, Crate, Bullet, BOTTOM, segment_box


def sandbox():
    game=Game();game.start();game.crates=[];game.obstacles=[];game.ammo_pickups=[]
    game.enemies=[Actor(1130,600,'sentry',timer=100)]
    game.grace=100
    return game


class Rules(unittest.TestCase):
    def test_two_d_has_no_vertical_input(self):
        game=sandbox();game.tick(.05,(0,1));self.assertEqual(game.player.y,BOTTOM+22)

    def test_free_movement_and_normalized_diagonal(self):
        a=sandbox();a.set_mode(3);x,y=a.player.x,a.player.y;a.tick(.05,(1,1))
        b=sandbox();b.set_mode(3);bx=b.player.x;b.tick(.05,(1,0))
        self.assertAlmostEqual(((a.player.x-x)**2+(a.player.y-y)**2)**.5,b.player.x-bx,places=5)
        self.assertGreater(a.player.y,y)

    def test_crate_reinterprets_floor_as_height(self):
        game=sandbox();game.set_mode(3);game.crates=[Crate(700,440)]
        game.tick(.05);self.assertEqual(game.crates[0].y,440)
        game.set_mode(2);game.tick(.05);self.assertLess(game.crates[0].y,440)
        height=game.crates[0].y
        game.set_mode(3);game.tick(.05)
        self.assertEqual(game.crates[0].y,height)

    def test_time_freezes_enemy_bullets_but_not_usage_clock(self):
        game=sandbox();game.bullets=[Bullet(500,300,200,0,'enemy')];game.set_mode(4)
        game.tick(.05);self.assertTrue(game.time_frozen);self.assertEqual(game.bullets[0].x,500)
        self.assertAlmostEqual(game.time_left,9.95);self.assertEqual(game.world_time,0)
        game.tick(.05,(1,0));self.assertFalse(game.time_frozen);self.assertGreater(game.bullets[0].x,500)

    def test_ten_second_exit_and_manual_exit_cost_exactly_one(self):
        game=sandbox();game.set_mode(4)
        for _ in range(201):game.tick(.05)
        self.assertEqual((game.mode,game.age),(3,21))
        game.set_mode(4);game.set_mode(2);self.assertEqual(game.age,22)
        game.set_mode(2);self.assertEqual(game.age,22)

    def test_rewind_moves_only_player_and_costs_age(self):
        game=sandbox();game.set_mode(3)
        for _ in range(120):game.tick(.025,(1,0))
        current=game.player.x;ammo=game.magazine;game.set_mode(4)
        self.assertTrue(game.rewind_points());game.select_rewind(index=len(game.rewind_points())-1)
        self.assertTrue(game.rewind());self.assertLess(game.player.x,current)
        self.assertEqual((game.mode,game.age,game.magazine),(3,21,ammo))

    def test_rewind_rejects_new_solid_at_recorded_position(self):
        game=sandbox();game.set_mode(3)
        for _ in range(80):game.tick(.025,(1,0))
        game.set_mode(4);points=game.rewind_points();x,y=points[0][1:3]
        game.obstacles=[(x-30,y-30,x+30,y+30)]
        self.assertFalse(game.rewind());self.assertEqual(game.age,20)

    def test_death_exponential_cost_and_checkpoint(self):
        game=sandbox()
        for expected in (21,23,27,35):
            game.die();self.assertEqual(game.age,expected)
            game.magazine=0;game.retry();self.assertEqual(game.magazine,6)
        game.die();self.assertEqual(game.state,'over');self.assertGreaterEqual(game.age,40)
        game.retry();self.assertEqual((game.age,game.room_index),(20,0))

    def test_four_d_death_includes_exit_cost(self):
        game=sandbox();game.set_mode(4);game.die();self.assertEqual(game.age,22)

    def test_aging_precision_and_speed(self):
        game=sandbox();young=game.speed;game.age=36
        self.assertEqual(game.precision,.1);self.assertLess(game.speed,young)

    def test_ammunition_conserved_during_reload(self):
        game=sandbox();game.magazine=2;game.reserve=7;self.assertTrue(game.reload())
        for _ in range(28):game.tick(.05)
        self.assertEqual((game.magazine,game.reserve),(6,3))
        self.assertFalse(game.reload())

    def test_pickup_throw_and_falling_attack(self):
        game=sandbox();game.crates=[Crate(game.player.x+50,game.player.y)]
        self.assertTrue(game.pickup());self.assertTrue(game.throw((900,300)));self.assertIsNone(game.held)
        game.enemies=[Actor(750,BOTTOM+22,'sentry')];game.grace=100
        game.crates=[Crate(750,BOTTOM+160)]
        for _ in range(30):game.tick(.025)
        self.assertFalse(game.enemies[0].alive)

    def test_swept_bullet_hits_instead_of_tunneling(self):
        game=sandbox();game.enemies=[Actor(650,300,'sentry')]
        game.bullets=[Bullet(600,300,2000,0,'player')];game.set_mode(3);game.tick(.05)
        self.assertFalse(game.enemies[0].alive)
        self.assertIsNotNone(segment_box(0,0,100,0,(45,-10,55,10)))

    def test_cover_intercepts_bullet_before_enemy(self):
        game=sandbox();game.set_mode(3);game.enemies=[Actor(700,300,'sentry')]
        game.crates=[Crate(650,300)];game.bullets=[Bullet(600,300,2000,0,'player')]
        game.tick(.05);self.assertTrue(game.enemies[0].alive);self.assertEqual(len(game.bullets),0)

    def test_all_twelve_chapters_reachable_and_streak_resets(self):
        game=sandbox();game.streak=3
        self.assertEqual(len(game.levels),12)
        for i in range(len(game.levels)):
            game.clear=True;self.assertTrue(game.next_room());self.assertEqual(game.streak,0)
        self.assertEqual(game.state,'won')

    def test_pause_model_does_not_consume_age_repeatedly(self):
        game=sandbox();game.age=39;game.set_mode(4);game.set_mode(3)
        self.assertEqual(game.state,'over');game.tick(.05);self.assertEqual(game.age,40)


if __name__=='__main__':unittest.main(verbosity=2)
