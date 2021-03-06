import unittest
from unittest.mock import Mock

from sc2.unit import Unit
from sc2.units import Units

from combat_micro import CombatMicro


class TestCombatMicro(unittest.IsolatedAsyncioTestCase):

    bot = Mock()
    combat_micro: CombatMicro = CombatMicro(bot)

    unit: Unit = Unit(Mock(), bot)
    empty_units = Units([], bot)

    async def test_main_target_initial(self):
        self.bot.enemy_start_locations = [1, 2, 3]
        await self.combat_micro.on_start()
        self.assertEqual(self.combat_micro.main_target, 1)

    def test_best_target_none_on_empty(self):
        self.assertIsNone(CombatMicro._best_target(self.unit, self.empty_units))


if __name__ == '__main__':
    unittest.main()
