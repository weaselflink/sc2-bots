from typing import List

import sc2
from sc2 import run_game, maps, Race, Difficulty, UnitTypeId
from sc2.player import Bot, Computer
from sc2.position import Point2
from sc2.units import Units


class WorkerRushBot(sc2.BotAI):
    def worker_count(self) -> int:
        return self.units.of_type(UnitTypeId.DRONE).amount

    def true_supply(self) -> float:
        return self.supply_left + self.already_pending(UnitTypeId.OVERLORD) * 8

    def maintain_supply(self):
        larvae: Units = self.larva

        if self.true_supply() < 2 and larvae and self.can_afford(UnitTypeId.OVERLORD):
            larvae.random.train(UnitTypeId.OVERLORD)
            return True
        else:
            return False

    def drone_up(self):
        if self.worker_count() < 80 and self.larva and self.can_afford(UnitTypeId.DRONE):
            self.larva.random.train(UnitTypeId.DRONE)

    def scatter_overlords(self):
        idle_overlords = self.units.of_type(UnitTypeId.OVERLORD).idle

        if idle_overlords:
            hq = self.townhalls.first.position
            exps: List[Point2] = sorted(self.expansion_locations_list, key=lambda target: target.position.distance_to(hq))

            moving_overlords = self.units.of_type(UnitTypeId.OVERLORD) - idle_overlords
            moving_to: List[Point2] = list(filter(lambda pos: pos is not None, [ol.order_target for ol in moving_overlords]))

            left: List[Point2] = [x for x in exps if x not in moving_to and x is not hq]
            for x in left:
                if idle_overlords:
                    idle_overlords.pop().move(x)

    async def build_spawning_pool(self):
        if self.spawning_pool_needed() and self.worker_count() > 12:
            if self.can_afford(UnitTypeId.SPAWNINGPOOL):
                await self.build(
                    UnitTypeId.SPAWNINGPOOL,
                    self.townhalls.first.position.towards(self.game_info.map_center, 5)
                )

    def spawning_pool_needed(self):
        return self.structures(UnitTypeId.SPAWNINGPOOL).amount + self.already_pending(
            UnitTypeId.SPAWNINGPOOL) < 1

    async def on_step(self, iteration):
        if self.maintain_supply():
            return

        self.scatter_overlords()
        self.drone_up()
        await self.build_spawning_pool()


run_game(maps.get("AcropolisLE"), [
    Bot(Race.Zerg, WorkerRushBot()),
    Computer(Race.Protoss, Difficulty.VeryEasy)
], realtime=True)
