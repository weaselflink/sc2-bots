
import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import *
from sc2.position import Point2
from sc2.units import Units


class SecondBot(sc2.BotAI):
    def worker_count(self) -> int:
        return self.units.of_type(UnitTypeId.SCV).amount

    def has_enemy_within(self, unit, dist):
        for enemy in self.enemy_units.not_structure:
            if enemy.distance_to(unit) < dist:
                self.chat_send("enemy")
                return True
        self.chat_send("no enemy")
        return False

    async def update_depots(self):
        for depot in self.structures(UnitTypeId.SUPPLYDEPOT).ready:
            if not self.has_enemy_within(depot, 15):
                depot(AbilityId.MORPH_SUPPLYDEPOT_LOWER)

        for depot in self.structures(UnitTypeId.SUPPLYDEPOTLOWERED).ready:
            if self.has_enemy_within(depot, 10):
                depot(AbilityId.MORPH_SUPPLYDEPOT_RAISE)

    async def build_depots(self):
        depots: Units = self.structures({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED})
        depot_placement_positions: Set[Point2] = self.main_base_ramp.corner_depots
        if self.supply_left < 2 and self.can_afford(UnitTypeId.SUPPLYDEPOT) and not self.already_pending(UnitTypeId.SUPPLYDEPOT):
            if depots.amount < 1:
                await self.build(UnitTypeId.SUPPLYDEPOT, depot_placement_positions.pop())
            elif depots.amount < 2:
                await self.build(UnitTypeId.SUPPLYDEPOT, depot_placement_positions.pop())
            else:
                await self.build(UnitTypeId.SUPPLYDEPOT, self.townhalls.first.position.towards(self.game_info.map_center, 8))

    async def on_step(self, iteration):
        await self.update_depots()
        await self.build_depots()

        idle_ccs = self.townhalls.idle
        if self.supply_left > 0 and idle_ccs:
            idle_ccs.first.train(UnitTypeId.SCV, can_afford_check=True)

        for scv in self.units(UnitTypeId.SCV).idle:
            scv.gather(self.mineral_field.closest_to(self.townhalls.first))


run_game(maps.get("AcropolisLE"), [
    Bot(Race.Terran, SecondBot()),
    Computer(Race.Protoss, Difficulty.VeryEasy)
], realtime=True)
