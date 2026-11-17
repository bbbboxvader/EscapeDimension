"""Room entry, startup gravity and navigable layout regressions."""
import sys
import unittest
from collections import deque
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Game, Actor, Crate, BOTTOM, LEFT, RIGHT, TOP


class RoomEntryTests(unittest.TestCase):
    def room(self, index):
        game = Game()
        game.room_index = index
        game.load_room()
        return game

    def test_all_rooms_start_without_overlap_or_dead_enemies(self):
        for index in range(5):
            with self.subTest(room=index+1):
                game = self.room(index)
                self.assertEqual(game.layout_errors(), [])
                self.assertTrue(all(e.alive for e in game.enemies))
                self.assertFalse(game.clear)
                self.assertEqual(game.kills, 0)

    def test_no_enemy_dies_from_passive_startup_gravity_in_any_room(self):
        for index in range(5):
            with self.subTest(room=index+1):
                game = self.room(index)
                initial = len(game.enemies)
                for _ in range(100):
                    game.tick(.02)
                self.assertEqual(sum(e.alive for e in game.enemies), initial)
                self.assertEqual(game.kills, 0)
                self.assertNotIn('hit', game.events)
                self.assertEqual(game.state, 'playing')

    def test_retry_recreates_all_enemies_without_world_progress(self):
        for index in range(5):
            game = self.room(index)
            game.kill(game.enemies[0])
            game.die()
            age = game.age
            game.retry()
            self.assertTrue(all(e.alive for e in game.enemies))
            self.assertEqual(game.world_time, 0)
            self.assertEqual(game.age, age)
            self.assertEqual(game.layout_errors(), [])

    def test_initial_crates_rest_on_a_real_support(self):
        for index in range(5):
            game = self.room(index)
            before = [(c.x, c.y) for c in game.crates]
            for _ in range(20):
                game.update_crates(.02)
            self.assertEqual(before, [(c.x, c.y) for c in game.crates])

    def test_player_created_fall_still_kills(self):
        game = self.room(0)
        game.obstacles = []
        game.crates = [Crate(850, 400)]
        game.enemies = [Actor(850, BOTTOM+22, 'sentry')]
        game.set_mode(3)
        game.set_mode(2)
        for _ in range(60):
            game.tick(.02)
        self.assertFalse(game.enemies[0].alive)

    def test_free_mode_has_route_from_spawn_to_upper_and_exit_areas(self):
        step = 20
        for index in range(5):
            game = self.room(index)
            def clear(x, y):
                box = (x-16, y-23, x+16, y+49)
                return (LEFT+16 <= x <= RIGHT-16 and BOTTOM+22 <= y <= TOP-49
                        and not any(game.overlap(box, r) for r in game.solids()))
            start = (int(game.player.x), int(game.player.y))
            todo, seen = deque([start]), {start}
            while todo:
                x,y = todo.popleft()
                for dx,dy in ((step,0),(-step,0),(0,step),(0,-step)):
                    point = x+dx,y+dy
                    if point not in seen and clear(*point):
                        seen.add(point)
                        todo.append(point)
            self.assertTrue(any(y > 540 for x,y in seen), f'room {index+1}: upper route')
            self.assertTrue(any(x > 1160 for x,y in seen), f'room {index+1}: exit route')


if __name__ == '__main__':
    unittest.main()
