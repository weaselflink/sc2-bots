from sc2 import UnitTypeId

from spin_bot_base import SpinBotBase


class ExperimentBot(SpinBotBase):

    async def build_depots(self):
        if (self.supply_left < 2 and
                self.can_afford(UnitTypeId.SUPPLYDEPOT) and
                not self.already_pending(UnitTypeId.SUPPLYDEPOT)):
            await self.build(
                UnitTypeId.SUPPLYDEPOT,
                self.townhalls.first.position.towards(self.game_info.map_center, 8)
            )

    async def on_step(self, iteration):
        await self.build_depots()
        await self.distribute_workers()
