"""Campaign, destructive cover, bosses and scrolling regression tests."""
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Game,Actor,Crate,Bullet,Grenade,BOSS_KINDS,LEFT,RIGHT,BOTTOM,TOP
from camera import Camera

def arena():
    g=Game();g.start();g.obstacles=[];g.crates=[];g.ammo_pickups=[]
    g.enemies=[Actor(1100,500,'sentry',timer=100)]
    g.grace=100;g.set_mode(3)
    return g

class CampaignTests(unittest.TestCase):
    def test_twelve_unique_large_chapters_and_exact_boss_placement(self):
        g=Game()
        self.assertEqual(len(g.levels),12)
        self.assertEqual(len({r['name'] for r in g.levels}),12)
        bosses=[]
        for i in range(12):
            g.room_index=i;g.load_room()
            self.assertGreaterEqual(g.right-g.left,2*(RIGHT-LEFT))
            self.assertGreaterEqual(g.top-g.bottom,2*(TOP-BOTTOM))
            for e in g.enemies:
                if e.kind in BOSS_KINDS:bosses.append((i+1,e.kind,e.hp))
        self.assertEqual(bosses,[(6,'midboss',18),(12,'finalboss',36)])

    def test_grenadiers_are_present_after_intro_and_in_final_chapter(self):
        g=Game()
        self.assertFalse(any(e[2]=='grenadier' for e in g.levels[0]['enemies']))
        for r in g.levels[1:]:self.assertTrue(any(e[2]=='grenadier' for e in r['enemies']))

    def test_far_enemies_do_not_attack_at_chapter_entry(self):
        g=Game();g.start();g.set_mode(3);g.grace=0
        e=next(e for e in g.enemies if e.x>1500)
        before=e.x,e.y,e.timer
        for _ in range(100):g.tick(.02)
        self.assertEqual(before,(e.x,e.y,e.timer))
        self.assertFalse(e.alerted)

    def test_midboss_blocks_progress_until_all_enemies_defeated(self):
        g=Game();g.room_index=5;g.load_room();g.grace=100
        boss=next(e for e in g.enemies if e.kind=='midboss')
        for e in g.enemies:
            if e is not boss:g.kill(e)
        g.tick(.02)
        self.assertFalse(g.clear);self.assertFalse(g.next_room())
        g.kill(boss);g.tick(.02)
        self.assertTrue(g.clear);self.assertTrue(g.next_room());self.assertEqual(g.room_index,6)

    def test_final_boss_clear_finishes_campaign(self):
        g=Game();g.room_index=11;g.load_room()
        for e in g.enemies:g.kill(e)
        g.tick(.02);self.assertTrue(g.clear)
        g.next_room();self.assertEqual(g.state,'won')

class ExplosiveTests(unittest.TestCase):
    def test_blast_destroys_wall_near_its_edge_not_just_its_centre(self):
        g=arena();near=(600,230,1100,260);far=(1200,300,1300,320)
        g.obstacles=[near,far]
        g.explode(Grenade(565,245,0,0,radius=100))
        self.assertNotIn(near,g.obstacles);self.assertIn(far,g.obstacles)
        self.assertGreater(len(g.fragments),0)

    def test_outer_bounds_and_reinforced_cover_survive(self):
        g=arena();bounds=g.bounds;r=(600,230,650,400)
        g.obstacles=[r];g.reinforced={r}
        g.explode(Grenade(600,250,0,0,radius=300))
        self.assertEqual(g.bounds,bounds);self.assertEqual(g.obstacles,[r])

    def test_crates_are_destroyed_and_held_reference_is_cleared(self):
        g=arena();g.crates=[Crate(550,300,held=True),Crate(950,300)]
        g.explode(Grenade(550,300,0,0,radius=120))
        self.assertEqual(len(g.crates),1);self.assertIsNone(g.held)

    def test_swept_grenade_collides_with_thin_wall(self):
        g=arena();g.obstacles=[(650,220,654,400)]
        g.grenades=[Grenade(600,300,3000,0,3,flight_time=5)]
        g.update_grenades(.05)
        self.assertFalse(g.grenades);self.assertFalse(g.obstacles)
        self.assertTrue(g.blasts);self.assertLess(g.blasts[0].x,655)

    def test_grenade_fuse_and_motion_freeze_but_four_d_limit_advances(self):
        g=arena();g.grenades=[Grenade(600,400,120,40,2,flight_time=4)]
        g.set_mode(4);n=g.grenades[0];before=n.x,n.y,n.fuse,n.age
        for _ in range(20):g.tick(.02)
        self.assertEqual(before,(n.x,n.y,n.fuse,n.age))
        self.assertLess(g.time_left,10)
        g.tick(.04,(1,0));self.assertGreater(n.x,before[0]);self.assertLess(n.fuse,before[2])

    def test_explosion_and_debris_animations_freeze_with_world(self):
        g=arena();g.obstacles=[(600,250,640,330)]
        g.explode(Grenade(600,300,0,0));g.set_mode(4)
        life=g.blasts[0].life;fragment=tuple(vars(g.fragments[0]).values())
        for _ in range(5):g.tick(.02)
        self.assertEqual(g.blasts[0].life,life)
        self.assertEqual(tuple(vars(g.fragments[0]).values()),fragment)

    def test_destroyed_cover_invalidates_enemy_route(self):
        g=arena();g.grace=0;g.player=Actor(1000,350)
        e=Actor(300,350,'knife');g.enemies=[e];g.obstacles=[(500,250,560,480)]
        g.chase(e,1,.02);self.assertIsNotNone(g._nav_signature)
        revision=g._nav_revision
        g.explode(Grenade(540,350,0,0,radius=100))
        self.assertEqual(e.route,[]);self.assertIsNone(g._nav_signature)
        g.chase(e,1,.02);self.assertGreater(g._nav_revision,revision)

    def test_retry_restores_walls_and_clears_live_grenades(self):
        g=Game();g.room_index=7;g.load_room();initial=list(g.obstacles)
        r=g.obstacles[0]
        g.explode(Grenade((r[0]+r[2])/2,(r[1]+r[3])/2,0,0))
        self.assertLess(len(g.obstacles),len(initial))
        g.grenades=[Grenade(700,300,50,0)]
        g.die();g.retry()
        self.assertEqual(g.obstacles,initial);self.assertFalse(g.grenades)
        self.assertFalse(g.blasts);self.assertFalse(g.fragments)

    def test_enemy_blast_can_hurt_other_enemies_but_not_its_owner(self):
        g=arena();owner=Actor(600,300,'grenadier');victim=Actor(670,300,'sentry')
        g.enemies=[owner,victim]
        g.explode(Grenade(630,320,0,0,source=owner))
        self.assertTrue(owner.alive);self.assertFalse(victim.alive)

    def test_grenadier_telegraphs_before_launch(self):
        g=arena();g.grace=0;e=Actor(700,300,'grenadier',timer=1.05)
        g.enemies=[e];g.player=Actor(300,300)
        g.update_enemies(.05)
        self.assertTrue(e.winding);self.assertFalse(g.grenades)
        e.timer=.01;g.update_enemies(.02)
        self.assertEqual(len(g.grenades),1);self.assertIn('grenade',g.events)

    def test_grenade_can_fly_beyond_original_screen_bounds(self):
        g=arena();g.grenades=[Grenade(2000,900,100,0,3,flight_time=5)]
        g.update_grenades(.05)
        self.assertEqual(len(g.grenades),1)
        self.assertGreater(g.grenades[0].x,2000)
        self.assertEqual(g.grenades[0].y,900)

    def test_unprotected_player_is_killed_inside_actual_blast_radius(self):
        g=arena();g.grace=0;g.player=Actor(500,300)
        g.explode(Grenade(550,320,0,0))
        self.assertEqual(g.state,'dead');self.assertFalse(g.player.alive)

class BossTests(unittest.TestCase):
    def test_rewind_rejects_overlap_with_large_boss_upper_body(self):
        g=arena();g.enemies=[Actor(800,300,'finalboss')]
        self.assertFalse(g.safe_position(845,370))
        self.assertTrue(g.safe_position(900,370))

    def test_regular_bullet_damages_boss_without_one_shot_kill(self):
        g=arena();boss=Actor(800,300,'midboss');g.enemies=[boss]
        g.bullets=[Bullet(750,330,1000,0,'player')]
        g.update_bullets(.05)
        self.assertTrue(boss.alive);self.assertEqual(boss.hp,17)

    def test_same_falling_crate_cannot_damage_boss_every_frame(self):
        g=arena();boss=Actor(800,176,'midboss');g.enemies=[boss]
        g.crates=[Crate(800,230,0,-250)]
        for _ in range(8):g.update_crates(.005)
        self.assertEqual(boss.hp,12)

    def test_boss_phase_changes_and_attack_patterns(self):
        for kind,max_hp,patterns in [('midboss',18,2),('finalboss',36,3)]:
            g=arena();g.grace=0;e=Actor(800,300,kind);g.enemies=[e]
            g.player=Actor(400,300);e.hp=max_hp//2
            for pattern in range(patterns):
                g.bullets=[];g.grenades=[];e.timer=0;e.attack_cycle=pattern
                e.winding=True;e.aim_x,e.aim_y=400,324
                g.update_boss(e,.01,400)
                self.assertEqual(e.phase,2)
                self.assertTrue(g.grenades if pattern==1 else g.bullets)
            if kind=='finalboss':
                e.hp=8;e.timer=5;g.update_boss(e,.01,400);self.assertEqual(e.phase,3)

    def test_boss_large_body_uses_a_collision_safe_route(self):
        g=arena();g.grace=0;e=Actor(260,340,'finalboss');g.enemies=[e]
        g.player=Actor(1000,340);g.obstacles=[(500,220,560,490)]
        for _ in range(450):
            g.chase(e,120,.02)
            self.assertFalse(g.overlap(e.box,g.obstacles[0]))
            if e.x>650:break
        self.assertGreater(e.x,650)

class CameraTests(unittest.TestCase):
    def test_camera_scrolls_and_keeps_aim_transform_invertible(self):
        c=Camera();c.follow(Actor(2000,800),(76,154,3200,1178))
        self.assertGreater(c.x,0);self.assertGreater(c.y,0)
        for p in [(0,0),(700,350),(1204,666)]:
            self.assertEqual(c.to_screen(*c.to_world(*p)),p)

    def test_camera_is_clamped_to_room_edges(self):
        c=Camera();bounds=(76,154,3200,1178)
        c.follow(Actor(90,176),bounds);self.assertEqual((c.x,c.y),(0,0))
        c.follow(Actor(3190,1150),bounds)
        self.assertEqual((c.x,c.y),(3200-RIGHT,1178-TOP))

if __name__=='__main__':unittest.main()
