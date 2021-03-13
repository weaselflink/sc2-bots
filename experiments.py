
import sc2
from sc2.constants import *
from sc2 import Union
from sc2.position import Point2
from sc2.unit import Unit


class FirstBot(sc2.BotAI):

    def has_building(self, where: Union[Unit, Point2]):
        return self.structures.closest_distance_to(where) < 0.5

    async def build_depots(self):
        if self.supply_left < 2 and self.can_afford(UnitTypeId.SUPPLYDEPOT) and not self.already_pending(UnitTypeId.SUPPLYDEPOT):
            await self.build(UnitTypeId.SUPPLYDEPOT, self.townhalls.first.position.towards(self.game_info.map_center, 8))

    async def on_step(self, iteration):
        await self.build_depots()
        await self.distribute_workers()
