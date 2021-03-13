
import sc2
from sc2.position import Point2
from sc2.unit import Unit


class SpinBot(sc2.BotAI):
    def has_building(self, where: sc2.Union[Unit, Point2]) -> bool:
        return self.structures.closest_distance_to(where) < 0.5

    def main_base(self) -> Unit:
        return self.start_location.closest(self.townhalls)

    def empty_geysers(self, base):
        base_geysers = self.vespene_geyser.closer_than(20, base)
        base_refineries = self.gas_buildings.closer_than(20, base)
        if base_refineries:
            return base_geysers.filter(lambda g: base_refineries.closest_distance_to(g) > 1)
        else:
            return base_geysers

    async def on_step(self, iteration: int):
        pass