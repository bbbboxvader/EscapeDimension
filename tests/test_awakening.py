"""Awakening progression, rotated input/gravity and distance-gated weapons."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Game,Actor,Crate,ThrownKnife,Grenade,Bullet,MIN_LETHAL_FALL
from camera import Camera
from space import turn_point,turn_box


def arena(chapter=0):
    g=Game();g.start();g.room_index=chapter;g.load_room()
    g.obstacles=[];g.crates=[];g.ammo_pickups=[];g.grace=100
    if chapter!=11:g.enemies=[Actor(1500,500,'sentry',timer=100)]
    g.player.x,g.player.y=(2544,300) if chapter==11 else (650,300)
    return g


class AwakeningTests(unittest.TestCase):
    def test_rotation_requires_sixth_chapter_clear_and_four_d(self):
        g=arena();g.set_mode(4);self.assertFalse(g.rotate_view(1))
        g.room_index=5;g.load_room();g.enemies=[];g.tick(.01)
        self.assertTrue(g.clear);self.assertTrue(g.awakened)
        self.assertFalse(g.rotate_view(1));g.set_mode(4);self.assertTrue(g.rotate_view(1))

    def test_unlock_survives_checkpoint_and_resets_on_new_run(self):
        g=arena(6);self.assertTrue(g.awakened)
        g.die();g.retry();self.assertTrue(g.awakened)
        g.start();self.assertFalse(g.awakened)

    def test_chapter_preview_grants_earned_power(self):
        for index in (6,11):self.assertTrue(arena(index).awakened)
        self.assertFalse(arena(5).awakened)

    def test_turn_is_reversible_and_does_not_spend_age_per_press(self):
        g=arena(6);g.set_mode(4);position=g.player.x,g.player.y
        for _ in range(4):g.rotate_view(1)
        self.assertEqual(g.view_turn,0);self.assertEqual(g.age,20)
        self.assertEqual((g.player.x,g.player.y),position)
        g.set_mode(3);self.assertEqual(g.age,21)

    def test_rotated_free_movement_matches_visible_wasd(self):
        for turn in range(4):
            g=arena(6);g.set_mode(4)
            for _ in range(turn):g.rotate_view(1)
            g.set_mode(3);before=g.player.x,g.player.y
            g.tick(.05,(1,0));after=g.player.x,g.player.y
            delta=turn_point(after[0]-before[0],after[1]-before[1],turn)
            self.assertAlmostEqual(delta[0],g.speed*.05);self.assertAlmostEqual(delta[1],0)

    def test_two_d_gravity_points_down_in_every_rotated_view(self):
        for turn in range(4):
            g=arena(6);g.set_mode(4)
            for _ in range(turn):g.rotate_view(1)
            g.set_mode(2);before=g.player.x,g.player.y
            g.tick(.05);delta=turn_point(g.player.x-before[0],g.player.y-before[1],turn)
            self.assertAlmostEqual(delta[0],0);self.assertLess(delta[1],0)
            self.assertEqual(g._local_depth,0)

    def test_rotated_jump_uses_visible_floor(self):
        g=arena(6);g.set_mode(4);g.rotate_view(1);g.set_mode(2)
        for _ in range(250):g.tick(.02)
        self.assertTrue(g.grounded);before=g.player.x,g.player.y
        self.assertTrue(g.jump());g.tick(.05)
        dx,dy=turn_point(g.player.x-before[0],g.player.y-before[1],1)
        self.assertAlmostEqual(dx,0);self.assertGreater(dy,0)

    def test_rotating_frozen_bomb_deflects_without_ticking_fuse(self):
        g=arena(11);g.grenades=[Grenade(2500,350,120,-80,fuse=2)]
        g.set_mode(4);g.tick(.01);bomb=g.grenades[0];before=bomb.fuse,bomb.age
        g.rotate_view(1);g.tick(.05)
        self.assertTrue(bomb.redirected);self.assertEqual(bomb.redirect_count,1)
        self.assertEqual((bomb.vx,bomb.vy),(80,120))
        self.assertEqual(before,(bomb.fuse,bomb.age));self.assertTrue(g.time_frozen)

    def test_rotated_two_d_bomb_falls_into_glass_and_damages_it(self):
        g=arena(11);g.player.x=2900;g.grace=0;g.laser_clock=g.bomb_clock=100
        g.grenades=[Grenade(2544,300,0,0,fuse=3,flight_time=10,source=g.enemies[0])]
        g.set_mode(4);g.rotate_view(1);g.rotate_view(1);g.set_mode(2)
        for _ in range(80):
            g.tick(.02)
            if g.command_window.hp<36:break
        self.assertEqual(g.command_window.hp,30)
        self.assertEqual(g.state,'playing');self.assertFalse(g.grenades)
        self.assertEqual(g.view_turn,2)

    def test_unturned_hostile_explosion_cannot_damage_glass(self):
        g=arena(11);g.explode(Grenade(2544,550,0,0))
        self.assertEqual(g.command_window.hp,36)

    def test_commander_throws_bombs_and_shoots_denser_waves(self):
        for damage,expected in ((0,3),(12,5),(24,7)):
            g=arena(11);g.grace=0;g.damage_window(damage);g.laser_clock=0;g.bomb_clock=0
            g.update_command_stage(.01)
            self.assertEqual(len(g.lasers),expected)
            self.assertGreaterEqual(len(g.grenades),1)
            self.assertTrue(all(not beam.active for beam in g.lasers))
            self.assertLessEqual(g.laser_clock,1.55)
            l,b,r,t=g.movement_bounds()
            safe=any(not any(g.overlap((x-15,y-22,x+15,y+48),beam.box) for beam in g.lasers)
                     for x in range(int(l+30),int(r-30),20) for y in range(int(b+25),int(t-50),15))
            self.assertTrue(safe)

    def test_four_d_stops_commander_bomb_clock(self):
        g=arena(11);g.grace=0;g.set_mode(4);before=g.bomb_clock
        for _ in range(20):g.tick(.02)
        self.assertEqual(g.bomb_clock,before);self.assertFalse(g.grenades)

    def test_retry_resets_view_and_bombs_but_keeps_awakening(self):
        g=arena(11);g.set_mode(4);g.rotate_view(1);g.grenades=[Grenade(2500,300,0,0)]
        g.die();g.retry()
        self.assertEqual(g.view_turn,0);self.assertTrue(g.awakened);self.assertFalse(g.grenades)

    def test_camera_round_trip_and_full_rotated_arena_fit(self):
        g=arena(11);c=Camera()
        for turn in range(4):
            c.follow(g.player,g.bounds,g.room['arena'],turn)
            for p in ((2544,300),(2344,548),(3108,666)):
                back=c.to_world(*c.to_screen(*p))
                self.assertAlmostEqual(back[0],p[0]);self.assertAlmostEqual(back[1],p[1])
            l,b,r,t=c.box(g.room['arena'])
            self.assertGreaterEqual(l,76-.001);self.assertLessEqual(r,1204+.001)
            self.assertGreaterEqual(b,154-.001);self.assertLessEqual(t,666+.001)

    def test_rotation_keeps_authored_maps_and_world_cover_unchanged(self):
        g=arena(6);g.obstacles=[(900,154,960,330)];before=g.obstacles[:];room=g.room.copy()
        g.set_mode(4);g.rotate_view(1)
        for _ in range(6):g.tick(.02,(1,0))
        self.assertEqual(g.obstacles,before);self.assertEqual(g.room,room)

    def test_swept_bullet_and_world_aim_match_after_rotation(self):
        g=arena(6);g.set_mode(4);g.rotate_view(1);g.set_mode(3)
        g.enemies=[Actor(650,550,'sentry',timer=100,body_turn=1)]
        for _ in range(30):g.tick(.02,aim=(650,550),firing=True)
        self.assertFalse(g.enemies[0].alive)


class FallingWeaponTests(unittest.TestCase):
    def test_one_knife_inventory_throw_and_recovery(self):
        g=arena();self.assertTrue(g.knife_owned)
        self.assertTrue(g.throw_knife((900,500)));self.assertFalse(g.knife_owned)
        self.assertFalse(g.throw_knife((900,500)));self.assertEqual(len(g.knives),1)
        g.knives[0].x,g.knives[0].y=g.player.x+20,g.player.y
        self.assertTrue(g.pickup());self.assertTrue(g.knife_owned);self.assertFalse(g.knives)

    def test_fast_horizontal_crate_and_knife_do_not_kill(self):
        for cls in (Crate,ThrownKnife):
            g=arena();g.set_mode(3);enemy=Actor(800,300,'sentry');g.enemies=[enemy]
            obj=cls(740,320,1000,0)
            if cls is Crate:g.crates=[obj]
            else:g.knives=[obj]
            for _ in range(10):g.update_crates(.02)
            self.assertTrue(enemy.alive);self.assertEqual(obj.fall_distance,0)

    def test_short_fall_is_not_lethal_even_at_high_velocity(self):
        for cls in (Crate,ThrownKnife):
            g=arena();enemy=Actor(800,176,'sentry');g.enemies=[enemy]
            obj=cls(800,260,0,-500)
            if cls is Crate:g.crates=[obj]
            else:g.knives=[obj]
            g.update_crates(.01);self.assertTrue(enemy.alive)
            self.assertLess(obj.fall_distance,MIN_LETHAL_FALL)

    def test_fall_threshold_is_measured_at_first_contact_not_end_of_tick(self):
        g=arena();enemy=Actor(800,176,'sentry');g.enemies=[enemy]
        # The crate's lower edge contacts the head after exactly 79px.
        g.crates=[Crate(800,326,0,-600)]
        for _ in range(6):g.update_crates(.05)
        self.assertTrue(enemy.alive)

    def test_long_real_fall_kills_for_both_weapons(self):
        for cls in (Crate,ThrownKnife):
            g=arena();enemy=Actor(800,176,'sentry');g.enemies=[enemy];obj=cls(800,450)
            if cls is Crate:g.crates=[obj]
            else:g.knives=[obj]
            for _ in range(60):g.update_crates(.02)
            self.assertFalse(enemy.alive);self.assertEqual(obj.fall_distance,0)

    def test_interrupted_fall_cannot_accumulate_across_two_ledges(self):
        g=arena();g.obstacles=[(700,250,900,270)];c=Crate(800,330);g.crates=[c]
        for _ in range(80):g.update_crates(.01)
        self.assertEqual(c.y,293);self.assertEqual(c.fall_distance,0)
        c.x=950;g.enemies=[Actor(950,176,'sentry')]
        for _ in range(30):g.update_crates(.01)
        self.assertTrue(g.enemies[0].alive)

    def test_mode_change_resets_fall_and_pickup_clears_damage_history(self):
        g=arena();c=Crate(g.player.x,g.player.y,fall_distance=100);g.crates=[c]
        c.hit_actors.add(123);g.pickup();self.assertEqual(c.fall_distance,0);self.assertFalse(c.hit_actors)
        c.fall_distance=100;g.set_mode(3);self.assertEqual(c.fall_distance,0)

    def test_knife_falls_toward_rotated_floor(self):
        g=arena(6);g.set_mode(4);g.rotate_view(1);g.set_mode(2)
        knife=ThrownKnife(850,350);g.knives=[knife]
        g.tick(.05);self.assertGreater(knife.x,850);self.assertAlmostEqual(knife.y,350)

    def test_death_checkpoint_restores_entry_knife(self):
        g=arena();g.throw_knife((900,500));g.die();g.retry()
        self.assertTrue(g.knife_owned);self.assertFalse(g.knives)

if __name__=='__main__':unittest.main()
