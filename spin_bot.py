
import sc2
from sc2 import UnitTypeId, Union
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class SpinBot(sc2.BotAI):
    def __init__(self):
        super().__init__()
        self.game_minutes: float = 0

    def has_building(self, where: sc2.Union[Unit, Point2]) -> bool:
        return self.structures.closest_distance_to(where) < 0.5

    def main_base(self) -> Unit:
        return self.start_location.closest(self.townhalls)

    def free_geysers(self, base):
        base_geysers = self.vespene_geyser.closer_than(20, base)
        base_refineries = self.gas_buildings.closer_than(20, base)
        if base_refineries:
            return base_geysers.filter(lambda g: base_refineries.closest_distance_to(g) > 1)
        else:
            return base_geysers

    async def fulfill_building_need(self, building_type: UnitTypeId, near: Union[Unit, Point2], count: int = 1):
        buildings = self.structures(building_type)
        if buildings.amount < count and not self.already_pending(building_type):
            await self.build(building_type, near)
            return True
        return False

    @staticmethod
    def center(units: Units) -> Unit:
        avg = Point2([0, 0])
        for u in units:
            avg += u.position
        avg /= units.amount
        return units.closest_to(avg)

    async def on_step(self, iteration: int):
        self.game_minutes = (self.state.game_loop / 22.4) / 60
