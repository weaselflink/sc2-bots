from typing import List

import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import *
from sc2.position import Point2
from sc2.units import Units


class SecondBot(sc2.BotAI):
    def worker_count(self) -> int:
        return self.units.of_type(UnitTypeId.SCV).amount

    async def on_step(self, iteration):
        cc = self.townhalls.first

        for depot in self.units.of_type(UnitTypeId.SUPPLYDEPOT).ready:
            for unit in self.enemy_units.not_structure:
                if unit.position.to2.distance_to(depot.position.to2) < 15:
                    break
            else:
                self.do(depot(UnitTypeId.MORPH_SUPPLYDEPOT_LOWER))

        for depot in self.units.of_type(UnitTypeId.SUPPLYDEPOTLOWERED).ready:
            for unit in self.enemy_units.not_structure:
                if unit.position.to2.distance_to(depot.position.to2) < 10:
                    self.do(depot(UnitTypeId.MORPH_SUPPLYDEPOT_RAISE))
                    break

        idle_ccs = self.townhalls.idle
        if self.supply_left > 0 and idle_ccs:
            idle_ccs.first.train(UnitTypeId.SCV, can_afford_check=True)

        if self.can_afford(UnitTypeId.SUPPLYDEPOT) and not self.already_pending(UnitTypeId.SUPPLYDEPOT) and self.supply_left < 2:
            if self.units.of_type(UnitTypeId.SUPPLYDEPOT).amount < 2:
                await self.build(UnitTypeId.SUPPLYDEPOT, self.main_base_ramp.corner_depots.pop())
            else:
                await self.build(UnitTypeId.SUPPLYDEPOT, cc.position.towards(self.game_info.map_center, 8))

        for scv in self.units.of_type(UnitTypeId.SCV).idle:
            self.do(scv.gather(self.mineral_field.closest_to(cc)))


run_game(maps.get("AcropolisLE"), [
    Bot(Race.Terran, SecondBot()),
    Computer(Race.Protoss, Difficulty.VeryEasy)
], realtime=True)
